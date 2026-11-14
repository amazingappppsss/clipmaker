"""Pipeline runner end-to-end: real DB, real storage, real FFmpeg, fake (free) AI providers.

Covers the PRD §8 reliability rules: no repeated stages, bounded retries, resume after a crash,
single runner per job, refunds on failure, honest terminal states.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from clipmaker.core.config import get_settings
from clipmaker.core.enums import ClipStatus, ProjectState
from clipmaker.db.models import Candidate, Clip, ProcessingJob, Transcript, User, VideoAnalysis
from clipmaker.db.session import get_session_factory
from clipmaker.pipeline import runner as runner_module
from clipmaker.pipeline.runner import NOT_YET_AVAILABLE_MESSAGE, JobRunner, Outcome
from clipmaker.providers.llm.base import LLMError
from clipmaker.storage.factory import get_storage
from conftest import upload_project
from pipeline_fakes import FakeLLM, FakeTranscriber


def make_runner(job_id: uuid.UUID, llm: Any, tx: Any, worker: str = "w1") -> JobRunner:
    return JobRunner(
        job_id,
        worker,
        get_settings(),
        get_storage(),
        get_session_factory(),
        llm_factory=lambda s: llm,
        transcriber_factory=lambda s: tx,
    )


@pytest.fixture
def started(
    client: TestClient, auth: dict[str, str], sample_video: Path, queued: list[uuid.UUID]
) -> tuple[str, uuid.UUID]:
    pid = upload_project(client, auth, sample_video)
    assert client.post(f"/projects/{pid}/process", headers=auth).status_code == 202
    return pid, queued[-1]


def _job(job_id: uuid.UUID) -> ProcessingJob:
    with get_session_factory()() as db:
        job = db.get(ProcessingJob, job_id)
        assert job is not None
        db.expunge(job)
        return job


def test_full_run_selects_clips(
    started: tuple[str, uuid.UUID], client: TestClient, auth: dict[str, str]
) -> None:
    pid, job_id = started
    llm, tx = FakeLLM(), FakeTranscriber()
    outcome, _ = make_runner(job_id, llm, tx).run()

    # Milestone 2 stops honestly before rendering, which isn't built yet.
    assert outcome == Outcome.PAUSED
    project = client.get(f"/projects/{pid}", headers=auth).json()
    assert project["state"] == "NEEDS_REVIEW"
    assert project["error_message"] == NOT_YET_AVAILABLE_MESSAGE
    assert project["thumbnail_url"] is not None

    job = _job(job_id)
    for stage in ("INGESTING", "TRANSCRIBING", "UNDERSTANDING", "SELECTING"):
        assert job.stages[stage]["status"] == "done"
    assert job.cost_usd > 0
    assert job.lease_owner is None

    clips = client.get(f"/projects/{pid}/clips", headers=auth).json()
    # Auto is a ceiling (about one per 90 s of transcript), not a quota; the fake transcript
    # holds six strong, non-overlapping stories, so all six clear the bar.
    assert 1 <= len(clips) <= 12
    for clip in clips:
        # Every pick explains itself: score, why it works, strengths, the five-second moment.
        assert clip["score"] and clip["why"] and isinstance(clip["strengths"], list)
        assert clip["five_second_moment"]
        assert clip["hook_type"] == "story_in_motion"
        if clip["teaser_text"]:  # flash-forward sits strictly inside the clip
            assert clip["start_seconds"] < clip["teaser_start_seconds"]
            assert clip["teaser_end_seconds"] < clip["end_seconds"]
        assert 20 <= clip["end_seconds"] - clip["start_seconds"] <= 90
        assert clip["title"] and clip["hook"] and len(clip["hashtags"]) == 3
        assert clip["status"] == ClipStatus.PLANNED.value
        assert clip["transcript"].startswith("So what was the moment")  # whole sentences
    assert [c["rank"] for c in clips] == list(range(1, len(clips) + 1))

    # The same cached transcript prefix is reused by analysis and selection (prompt caching).
    smart = [r for r in llm.requests if r.tier == "smart"]
    assert len({(r.system, r.context) for r in smart}) == 1

    with get_session_factory()() as db:
        reasons = db.scalars(
            select(Candidate.rejected_reason).where(Candidate.selected.is_(False))
        ).all()
        assert "overlaps a stronger moment" in reasons
        assert all(reasons), "every rejected candidate records why"

    status = client.get(f"/projects/{pid}/status", headers=auth).json()
    assert [s["status"] for s in status["stages"]][:4] == ["done"] * 4
    assert status["stages"][4]["status"] == "pending"


def test_rerun_does_not_repeat_completed_work(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    llm, tx = FakeLLM(), FakeTranscriber()
    make_runner(job_id, llm, tx).run()
    calls = (tx.calls, len(llm.requests))
    # Force the job back to a runnable state as if a redelivered task arrived.
    with get_session_factory()() as db:
        job = db.get(ProcessingJob, job_id)
        assert job is not None
        job.state = ProjectState.SELECTING
        db.commit()
    make_runner(job_id, llm, tx).run()
    assert (tx.calls, len(llm.requests)) == calls  # no paid call was made twice


def test_transient_failure_retries_then_succeeds(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    llm, tx = FakeLLM(), FakeTranscriber(fail_times=2, retryable=True)
    assert make_runner(job_id, llm, tx).run() == (Outcome.RETRY, 30)
    assert make_runner(job_id, llm, tx).run() == (Outcome.RETRY, 120)
    assert make_runner(job_id, llm, tx).run()[0] == Outcome.PAUSED
    job = _job(job_id)
    assert job.stages["TRANSCRIBING"]["attempts"] == 3
    assert job.retry_count == 2


def test_retries_are_bounded_and_credits_refunded(
    started: tuple[str, uuid.UUID], client: TestClient, auth: dict[str, str]
) -> None:
    pid, job_id = started
    before = client.get("/account/usage", headers=auth).json()["credits_balance"]
    llm, tx = FakeLLM(), FakeTranscriber(fail_times=99, retryable=True)
    outcomes = [
        make_runner(job_id, llm, tx).run()[0] for _ in range(get_settings().stage_max_attempts)
    ]
    assert outcomes[-1] == Outcome.FAILED
    assert make_runner(job_id, llm, tx).run()[0] == Outcome.SKIPPED  # terminal: never runs again
    project = client.get(f"/projects/{pid}", headers=auth).json()
    assert project["state"] == "FAILED" and "refunded" in project["error_message"]
    after = client.get("/account/usage", headers=auth).json()["credits_balance"]
    assert after == before + 1  # the 12-second video cost 1 credit


def test_permanent_failure_fails_fast(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    llm = FakeLLM(fail_with=LLMError("The model declined this content", retryable=False))
    assert make_runner(job_id, llm, FakeTranscriber()).run()[0] == Outcome.FAILED
    job = _job(job_id)
    assert job.stages["UNDERSTANDING"]["attempts"] == 1
    assert job.error_code == "analysis_failed"


def test_resume_after_crash_and_retry_of_failed_project(
    started: tuple[str, uuid.UUID],
    client: TestClient,
    auth: dict[str, str],
    queued: list[uuid.UUID],
) -> None:
    pid, job_id = started
    tx = FakeTranscriber()
    # First run: analysis fails permanently after ingest+transcription succeeded.
    make_runner(job_id, FakeLLM(fail_with=LLMError("bad", retryable=False)), tx).run()
    # User retries: same job resumes, transcription is NOT paid for again.
    assert client.post(f"/projects/{pid}/process", headers=auth).status_code == 202
    assert queued[-1] == job_id
    assert make_runner(job_id, FakeLLM(), tx).run()[0] == Outcome.PAUSED
    assert tx.calls == 1
    with get_session_factory()() as db:
        assert db.query(Transcript).count() == 1 and db.query(VideoAnalysis).count() == 1


def test_lease_prevents_concurrent_runners(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    holder = make_runner(job_id, FakeLLM(), FakeTranscriber(), worker="a")
    assert holder._acquire_lease()
    assert make_runner(job_id, FakeLLM(), FakeTranscriber(), worker="b").run()[0] == Outcome.SKIPPED


def test_expired_lease_is_taken_over(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    from datetime import UTC, datetime, timedelta

    with get_session_factory()() as db:
        job = db.get(ProcessingJob, job_id)
        assert job is not None
        job.lease_owner, job.lease_expires_at = (
            "dead-worker",
            datetime.now(UTC) - timedelta(minutes=1),
        )
        db.commit()
    assert make_runner(job_id, FakeLLM(), FakeTranscriber(), worker="b").run()[0] == Outcome.PAUSED


def test_deleted_project_cancels_job(
    started: tuple[str, uuid.UUID], client: TestClient, auth: dict[str, str]
) -> None:
    pid, job_id = started
    client.delete(f"/projects/{pid}", headers=auth)
    assert make_runner(job_id, FakeLLM(), FakeTranscriber()).run()[0] in (
        Outcome.SKIPPED,
        Outcome.CANCELLED,
    )


def test_all_stages_registered_completes(
    started: tuple[str, uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When later milestones register every stage, the job ends COMPLETED."""
    _, job_id = started
    from clipmaker.pipeline.context import StageOutput

    handlers = dict(runner_module.STAGE_HANDLERS)
    for stage in (ProjectState.EDITING, ProjectState.RENDERING, ProjectState.QUALITY_CHECK):
        handlers[stage] = lambda ctx: StageOutput({"ok": True})
    r = JobRunner(
        job_id,
        "w",
        get_settings(),
        get_storage(),
        get_session_factory(),
        handlers=handlers,
        llm_factory=lambda s: FakeLLM(),
        transcriber_factory=lambda s: FakeTranscriber(),
    )
    assert r.run()[0] == Outcome.COMPLETED
    assert _job(job_id).state == ProjectState.COMPLETED


def test_stale_job_detection(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    from datetime import UTC, datetime, timedelta

    from clipmaker.services.processing import stale_job_ids

    with get_session_factory()() as db:
        assert job_id not in stale_job_ids(db, timedelta(minutes=10))
        job = db.get(ProcessingJob, job_id)
        assert job is not None
        job.lease_owner, job.lease_expires_at = "dead", datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        assert job_id in stale_job_ids(db, timedelta(minutes=10))


def test_clip_rows_reference_candidates(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    make_runner(job_id, FakeLLM(), FakeTranscriber()).run()
    with get_session_factory()() as db:
        for clip in db.scalars(select(Clip)):
            cand = db.get(Candidate, clip.candidate_id)
            assert cand is not None and cand.selected
            assert clip.edit_plan["start"] == cand.start_seconds
        assert db.query(User).count() == 1


def test_restart_resumes_interrupted_jobs_immediately(started: tuple[str, uuid.UUID]) -> None:
    """A job cut off by a redeploy is re-queued at startup, not after the lease expires."""
    _, job_id = started
    from datetime import UTC, datetime, timedelta

    from clipmaker.workers.recover import recover_interrupted_jobs

    with get_session_factory()() as db:
        job = db.get(ProcessingJob, job_id)
        assert job is not None
        job.state = ProjectState.SELECTING
        job.lease_owner, job.lease_expires_at = (
            "old-container",
            datetime.now(UTC) + timedelta(minutes=14),
        )
        db.commit()
        queued: list[uuid.UUID] = []
        assert recover_interrupted_jobs(db, queued.append) == [job_id] == queued
    resumed = make_runner(job_id, FakeLLM(), FakeTranscriber())
    assert resumed.run()[0] in (Outcome.PAUSED, Outcome.COMPLETED)

    with get_session_factory()() as db:  # finished jobs are left alone
        assert recover_interrupted_jobs(db, lambda _: None) == []


def test_share_link_shows_moments_read_only_and_can_be_revoked(
    started: tuple[str, uuid.UUID], client: TestClient, auth: dict[str, str]
) -> None:
    pid, job_id = started
    make_runner(job_id, FakeLLM(), FakeTranscriber()).run()

    token = client.post(f"/projects/{pid}/share", headers=auth).json()["token"]
    assert client.post(f"/projects/{pid}/share", headers=auth).json()["token"] == token

    shared = client.get(f"/share/{token}")  # no auth needed
    assert shared.status_code == 200
    body = shared.json()
    assert body["clips"] and body["clips"][0]["why"]
    assert "source_video_url" not in body  # video files are never exposed by a link

    client.delete(f"/projects/{pid}/share", headers=auth)
    assert client.get(f"/share/{token}").status_code == 404


def test_only_the_owner_can_share(
    started: tuple[str, uuid.UUID], client: TestClient, other_auth: dict[str, str]
) -> None:
    pid, _ = started
    assert client.post(f"/projects/{pid}/share", headers=other_auth).status_code == 404


def test_cancel_stops_paid_work_and_refunds(
    started: tuple[str, uuid.UUID], client: TestClient, auth: dict[str, str]
) -> None:
    pid, job_id = started
    before = client.get("/account/usage", headers=auth).json()["credits_balance"]
    res = client.post(f"/projects/{pid}/cancel", headers=auth)
    assert res.status_code == 200 and res.json()["state"] == "CANCELLED"
    assert client.get("/account/usage", headers=auth).json()["credits_balance"] > before

    llm = FakeLLM()
    assert make_runner(job_id, llm, FakeTranscriber()).run()[0] in (
        Outcome.SKIPPED,
        Outcome.CANCELLED,
    )
    assert llm.requests == []  # no AI calls after cancelling
    assert client.post(f"/projects/{pid}/cancel", headers=auth).status_code == 409

    # Cancelled projects can be started again (credits charged again, completed steps kept).
    assert client.post(f"/projects/{pid}/process", headers=auth).status_code == 202


def test_cancel_mid_stage_stops_at_next_checkpoint(started: tuple[str, uuid.UUID]) -> None:
    _, job_id = started
    from clipmaker.pipeline.errors import JobCancelledError

    runner = make_runner(job_id, FakeLLM(), FakeTranscriber())
    assert runner._acquire_lease()
    with get_session_factory()() as db:
        job = db.get(ProcessingJob, job_id)
        assert job is not None
        job.state = ProjectState.CANCELLED
        db.commit()
    with pytest.raises(JobCancelledError):
        runner.heartbeat()
