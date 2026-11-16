"""Correcting a clip the AI got wrong.

The product's real gap is that a wrong decision cannot be fixed, so these cover the parts that
would quietly make a correction useless: being overwritten by re-planning, being ignored, or
leaving the old video in place so nothing visibly changes.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.enums import AssetKind, ClipStatus, ProjectState
from clipmaker.db.models import Clip, ClipAsset, ProcessingJob, Project, User
from clipmaker.pipeline.stages.edit import MIN_CLIP_SECONDS, TRIM_LIMIT, apply_trim
from clipmaker.services import corrections

PLAN = {"start": 100.0, "end": 140.0, "start_segment": 0, "end_segment": 3}


# --- the pure part: what a trim is allowed to do ----------------------------------------


def test_no_correction_leaves_the_clip_alone() -> None:
    assert apply_trim(PLAN, None) == (100.0, 140.0)
    assert apply_trim(PLAN, {}) == (100.0, 140.0)


def test_a_trim_moves_the_edges() -> None:
    assert apply_trim(PLAN, {"start": 95.0, "end": 150.0}) == (95.0, 150.0)
    assert apply_trim(PLAN, {"start": 110.0}) == (110.0, 140.0)
    assert apply_trim(PLAN, {"end": 130.0}) == (100.0, 130.0)


def test_a_trim_cannot_wander_off_and_become_a_different_clip() -> None:
    start, end = apply_trim(PLAN, {"start": 0.0, "end": 9999.0})
    assert start == 100.0 - TRIM_LIMIT
    assert end == 140.0 + TRIM_LIMIT


def test_nonsense_is_clamped_rather_than_refused() -> None:
    """A stored correction must never be able to wedge a later re-render."""
    start, end = apply_trim(PLAN, {"start": 139.0, "end": 101.0})
    assert end - start >= MIN_CLIP_SECONDS
    assert apply_trim({**PLAN, "start": 1.0, "end": 9.0}, {"start": -50.0})[0] == 0.0


def test_a_correction_survives_the_ai_replanning_the_clip() -> None:
    """`corrections` lives apart from `edit_plan` precisely so this holds."""
    replanned = {**PLAN, "start": 102.0, "end": 138.0}  # the AI changed its mind
    assert apply_trim(replanned, {"start": 95.0}) == (95.0, 138.0)


# --- the endpoint -------------------------------------------------------------------------


@pytest.fixture
def finished_clip(db: Session, auth: dict[str, str]) -> tuple[Project, Clip]:
    """A completed project with one rendered clip, owned by Alice."""
    user = User(id=uuid.uuid5(uuid.NAMESPACE_URL, "alice@example.com"), email="alice@example.com")
    db.add(user)
    project = Project(
        user_id=user.id, title="Episode", state=ProjectState.COMPLETED, settings={}
    )
    db.add(project)
    db.flush()
    clip = Clip(
        project_id=project.id,
        rank=1,
        status=ClipStatus.READY,
        style="bold",
        edit_plan={**PLAN, "render": {"pieces": [], "duration": 40.0}},
    )
    db.add(clip)
    db.flush()
    db.add(
        ClipAsset(
            clip_id=clip.id,
            kind=AssetKind.VIDEO,
            storage_key="k/clip.mp4",
            size_bytes=1234,
            is_final=True,
        )
    )
    db.add(ProcessingJob(project_id=project.id, state=ProjectState.COMPLETED, stages={
        "TRANSCRIBING": {"status": "done"},
        "EDITING": {"status": "done"},
        "RENDERING": {"status": "done"},
    }))
    db.commit()
    return project, clip


def test_a_trim_queues_a_rebuild_of_just_that_clip(
    client: TestClient, auth: dict[str, str], db: Session, finished_clip: tuple[Project, Clip]
) -> None:
    project, clip = finished_clip
    res = client.patch(
        f"/projects/{project.id}/clips/{clip.id}",
        json={"start_seconds": 95.0},
        headers=auth,
    )
    assert res.status_code == 202, res.text

    db.expire_all()
    fresh = db.get(Clip, clip.id)
    assert fresh is not None
    assert fresh.corrections == {"start": 95.0}
    # The AI's plan is dropped so EDITING rebuilds it; the moment it was planned from stays.
    assert "render" not in fresh.edit_plan
    assert fresh.edit_plan["start"] == 100.0
    assert fresh.status == ClipStatus.PLANNED
    assert fresh.attempts == 0
    # The old video has to go, or RENDERING skips the clip and nothing visibly changes.
    assert [a for a in fresh.assets if a.kind == AssetKind.VIDEO] == []

    job = db.scalars(select(ProcessingJob)).one()
    assert "RENDERING" not in dict(job.stages)
    assert "TRANSCRIBING" in dict(job.stages), "the expensive stages must not be redone"


def test_corrections_accumulate_rather_than_replace(
    client: TestClient, auth: dict[str, str], db: Session, finished_clip: tuple[Project, Clip]
) -> None:
    project, clip = finished_clip
    url = f"/projects/{project.id}/clips/{clip.id}"
    assert client.patch(url, json={"start_seconds": 95.0}, headers=auth).status_code == 202

    db.expire_all()
    project_row = db.get(Project, project.id)
    assert project_row is not None
    project_row.state = ProjectState.COMPLETED  # pretend the rebuild finished
    db.commit()

    assert client.patch(url, json={"end_seconds": 150.0}, headers=auth).status_code == 202
    db.expire_all()
    fresh = db.get(Clip, clip.id)
    assert fresh is not None
    assert fresh.corrections == {"start": 95.0, "end": 150.0}


def test_an_empty_correction_is_refused(
    client: TestClient, auth: dict[str, str], finished_clip: tuple[Project, Clip]
) -> None:
    project, clip = finished_clip
    res = client.patch(f"/projects/{project.id}/clips/{clip.id}", json={}, headers=auth)
    assert res.status_code == 409


def test_a_clip_cannot_be_corrected_mid_run(
    client: TestClient, auth: dict[str, str], db: Session, finished_clip: tuple[Project, Clip]
) -> None:
    project, clip = finished_clip
    row = db.get(Project, project.id)
    assert row is not None
    row.state = ProjectState.RENDERING
    db.commit()
    res = client.patch(
        f"/projects/{project.id}/clips/{clip.id}", json={"start_seconds": 95.0}, headers=auth
    )
    assert res.status_code == 409


def test_nobody_can_correct_someone_elses_clip(
    client: TestClient, other_auth: dict[str, str], finished_clip: tuple[Project, Clip]
) -> None:
    project, clip = finished_clip
    res = client.patch(
        f"/projects/{project.id}/clips/{clip.id}",
        json={"start_seconds": 95.0},
        headers=other_auth,
    )
    assert res.status_code == 404


def test_an_unknown_clip_is_not_found(
    client: TestClient, auth: dict[str, str], finished_clip: tuple[Project, Clip]
) -> None:
    project, _ = finished_clip
    res = client.patch(
        f"/projects/{project.id}/clips/{uuid.uuid4()}",
        json={"start_seconds": 95.0},
        headers=auth,
    )
    assert res.status_code == 404
