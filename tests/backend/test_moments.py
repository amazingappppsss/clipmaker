"""The moments we scored but did not ship, and promoting one into a clip.

Other clippers hand you N clips and keep the rest. These cover the behaviour that makes
showing the rest trustworthy: the rejected ones really are listed with their reasons, a
promoted one really becomes a clip, and nothing can be promoted twice or out from under a
running pipeline.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.enums import ClipStatus, ProjectState
from clipmaker.db.models import Candidate, Clip, ProcessingJob, Project, User
from clipmaker.services import moments


def _plan(start: float, end: float) -> dict:
    return {
        "start": start,
        "end": end,
        "start_segment": 0,
        "end_segment": 2,
        "transcript": "He walked away from the money.",
        "hook_line": "He walked away from the money",
        "notes": [],
        "teaser": None,
    }


@pytest.fixture
def scored_project(db: Session) -> tuple[Project, Candidate, Candidate]:
    """A finished project: one moment shipped, one rejected but promotable."""
    user = User(id=uuid.uuid5(uuid.NAMESPACE_URL, "alice@example.com"), email="alice@example.com")
    db.add(user)
    project = Project(user_id=user.id, title="Episode", state=ProjectState.COMPLETED, settings={})
    db.add(project)
    db.flush()

    shipped = Candidate(
        project_id=project.id,
        start_seconds=10.0,
        end_seconds=40.0,
        category="story",
        rationale="Opens on a number nobody expects.",
        scores={"hook": 9, "hook_type": "shocking_number"},
        total_score=88.0,
        selected=True,
        plan=_plan(10.0, 40.0),
    )
    missed = Candidate(
        project_id=project.id,
        start_seconds=300.0,
        end_seconds=335.0,
        category="story",
        rationale="Good story, but it overlaps a stronger moment.",
        scores={"hook": 6, "hook_type": "confession"},
        total_score=61.0,
        selected=False,
        rejected_reason="not in the top picks",
        plan=_plan(300.0, 335.0),
    )
    db.add_all([shipped, missed])
    db.add(
        Clip(
            project_id=project.id,
            candidate_id=shipped.id,
            rank=1,
            status=ClipStatus.READY,
            style="bold",
            edit_plan=_plan(10.0, 40.0),
        )
    )
    db.add(
        ProcessingJob(
            project_id=project.id,
            state=ProjectState.COMPLETED,
            stages={
                "TRANSCRIBING": {"status": "done"},
                "RENDERING": {"status": "done"},
            },
        )
    )
    db.commit()
    return project, shipped, missed


def test_the_rejected_moments_are_listed_with_their_reasons(
    client: TestClient, auth: dict[str, str], scored_project: tuple[Project, Candidate, Candidate]
) -> None:
    project, _, missed = scored_project
    body = client.get(f"/projects/{project.id}/moments", headers=auth).json()

    assert body["scanned"] == 2
    assert body["shipped"] == 1
    # Best first, so the rejected one with the lower score comes second.
    rejected = body["moments"][1]
    assert rejected["id"] == str(missed.id)
    assert rejected["selected"] is False
    assert rejected["rejected_reason"] == "not in the top picks"
    assert rejected["score"] == 61
    assert rejected["why"]
    assert rejected["can_promote"] is True
    assert body["moments"][0]["can_promote"] is False, "an already shipped moment is not promotable"


def test_promoting_a_moment_makes_it_a_clip_and_queues_a_render(
    client: TestClient,
    auth: dict[str, str],
    db: Session,
    scored_project: tuple[Project, Candidate, Candidate],
) -> None:
    project, _, missed = scored_project
    res = client.post(f"/projects/{project.id}/moments/{missed.id}/promote", headers=auth)
    assert res.status_code == 202, res.text

    db.expire_all()
    clip = db.scalar(select(Clip).where(Clip.candidate_id == missed.id))
    assert clip is not None
    assert clip.status == ClipStatus.PLANNED
    assert clip.rank == 2, "promoted clips join the end rather than reshuffling the AI's order"
    assert clip.edit_plan["start"] == 300.0
    assert "render" not in clip.edit_plan, "EDITING has to plan it"

    row = db.get(Candidate, missed.id)
    assert row is not None
    assert row.selected is True
    assert row.rejected_reason is None

    job = db.scalars(select(ProcessingJob)).one()
    assert job.state == ProjectState.EDITING
    assert "RENDERING" not in dict(job.stages)
    assert "TRANSCRIBING" in dict(job.stages), "the expensive stages must not be redone"


def test_a_moment_cannot_be_promoted_twice(
    client: TestClient,
    auth: dict[str, str],
    db: Session,
    scored_project: tuple[Project, Candidate, Candidate],
) -> None:
    project, _, missed = scored_project
    url = f"/projects/{project.id}/moments/{missed.id}/promote"
    assert client.post(url, headers=auth).status_code == 202

    row = db.get(Project, project.id)
    assert row is not None
    row.state = ProjectState.COMPLETED  # pretend the render finished
    db.commit()

    assert client.post(url, headers=auth).status_code == 409


def test_a_moment_scored_before_plans_were_stored_says_so(
    client: TestClient,
    auth: dict[str, str],
    db: Session,
    scored_project: tuple[Project, Candidate, Candidate],
) -> None:
    """Rather than failing halfway through a render."""
    project, _, missed = scored_project
    row = db.get(Candidate, missed.id)
    assert row is not None
    row.plan = {}
    db.commit()

    assert moments.can_promote(row) is False
    body = client.get(f"/projects/{project.id}/moments", headers=auth).json()
    assert body["moments"][1]["can_promote"] is False
    res = client.post(f"/projects/{project.id}/moments/{missed.id}/promote", headers=auth)
    assert res.status_code == 409


def test_nothing_can_be_promoted_mid_run(
    client: TestClient,
    auth: dict[str, str],
    db: Session,
    scored_project: tuple[Project, Candidate, Candidate],
) -> None:
    project, _, missed = scored_project
    row = db.get(Project, project.id)
    assert row is not None
    row.state = ProjectState.RENDERING
    db.commit()
    res = client.post(f"/projects/{project.id}/moments/{missed.id}/promote", headers=auth)
    assert res.status_code == 409


def test_moments_are_private_to_their_owner(
    client: TestClient,
    other_auth: dict[str, str],
    scored_project: tuple[Project, Candidate, Candidate],
) -> None:
    project, _, missed = scored_project
    assert client.get(f"/projects/{project.id}/moments", headers=other_auth).status_code == 404
    assert (
        client.post(
            f"/projects/{project.id}/moments/{missed.id}/promote", headers=other_auth
        ).status_code
        == 404
    )
