"""Every moment we scored — including the ones we didn't ship.

Other clippers hand you N clips and keep the rest to themselves. If their AI skipped the best
bit of your episode, you never find out it was ever considered.

We already score every candidate and record why each one missed: "not in the top picks",
"below the quality bar", "overlaps a stronger moment". Throwing that away in the interface was
never a decision, just an omission. Showing it costs us nothing — no extra AI call, the rows
are already in the database — and it answers the one thing a creator cannot otherwise check:
did it actually look at my whole episode?

Promoting a near-miss into a real clip reuses the correction machinery rather than adding a
second path, and is not charged: the episode was paid for once.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.enums import ClipStatus, ProjectState
from clipmaker.core.errors import ConflictError, NotFoundError
from clipmaker.db.models import Candidate, Clip, ProcessingJob, Project
from clipmaker.schemas import MomentOut, MomentsOut
from clipmaker.services.corrections import REPLAY_STAGES

logger = logging.getLogger(__name__)

#: A promoted moment has to be buildable: EDITING needs these to make a render plan.
_REQUIRED_PLAN_KEYS = ("start", "end", "start_segment", "end_segment")

_PROMOTABLE = (ProjectState.COMPLETED, ProjectState.NEEDS_REVIEW, ProjectState.FAILED)


def list_moments(db: Session, project: Project) -> list[Candidate]:
    """Every scored moment, best first. Includes the ones that did not make the cut."""
    return list(
        db.scalars(
            select(Candidate)
            .where(Candidate.project_id == project.id)
            .order_by(Candidate.total_score.desc())
        ).all()
    )


def can_promote(candidate: Candidate) -> bool:
    """Whether this moment can still be turned into a clip.

    Moments scored before we started storing a buildable plan cannot be, and say so, rather
    than failing halfway through a render.
    """
    plan = candidate.plan or {}
    return all(plan.get(k) is not None for k in _REQUIRED_PLAN_KEYS)


def promote(
    db: Session, project: Project, candidate_id: uuid.UUID, enqueue_state: bool = True
) -> ProcessingJob:
    """Turn a moment we rejected into a real clip and queue it to be rendered.

    Raises:
        NotFoundError: no such moment in this project.
        ConflictError: the project is busy, the moment is already a clip, or it predates
            stored plans and cannot be rebuilt.
    """
    if project.state not in _PROMOTABLE:
        raise ConflictError("Wait for this video to finish before adding a clip.")

    candidate = db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.project_id == project.id)
    )
    if candidate is None:
        raise NotFoundError("Moment not found")

    existing = db.scalar(select(Clip).where(Clip.candidate_id == candidate.id))
    if existing is not None:
        raise ConflictError("That moment is already one of your clips.")
    if not can_promote(candidate):
        raise ConflictError("This moment was scored before clips could be added by hand.")

    plan: dict[str, Any] = dict(candidate.plan)
    story = (candidate.scores or {}).get("story")
    hook = str(plan.get("hook_line") or candidate.rationale)[:300]

    # Ranked last: promoted clips join the end of the list rather than reshuffling the AI's
    # ordering, which the viewer may already have worked through.
    last = db.scalar(
        select(Clip.rank).where(Clip.project_id == project.id).order_by(Clip.rank.desc())
    )
    clip = Clip(
        project_id=project.id,
        candidate_id=candidate.id,
        rank=(last or 0) + 1,
        status=ClipStatus.PLANNED,
        title=hook[:200],
        hook=hook,
        alt_titles=[],
        hashtags=[],
        style=str((project.settings or {}).get("style") or "bold"),
        edit_plan={
            "start": plan["start"],
            "end": plan["end"],
            "start_segment": plan["start_segment"],
            "end_segment": plan["end_segment"],
            "transcript": plan.get("transcript"),
            "notes": [*(plan.get("notes") or []), "added by hand from the rejected moments"],
            "teaser": plan.get("teaser"),
        },
    )
    db.add(clip)
    candidate.selected = True
    candidate.rejected_reason = None

    job = db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.project_id == project.id)
        .order_by(ProcessingJob.created_at.desc())
    )
    if job is None:
        job = ProcessingJob(project_id=project.id, state=ProjectState.EDITING, stages={})
        db.add(job)
    else:
        job.stages = {k: v for k, v in (job.stages or {}).items() if k not in REPLAY_STAGES}
        job.state = ProjectState.EDITING
        job.error_code = job.error_detail = None
        job.completed_at = None

    project.state = ProjectState.EDITING
    project.error_message = None
    db.commit()
    db.refresh(job)
    logger.info(
        "moment_promoted",
        extra={"candidate_id": str(candidate.id), "score": candidate.total_score},
    )
    _ = story  # kept for a future titling pass; not used yet
    return job


def as_output(db: Session, project: Project) -> MomentsOut:
    """The moments, shaped for the API."""
    from clipmaker.schemas import MomentsOut

    rows = list_moments(db, project)
    return MomentsOut(
        scanned=len(rows),
        shipped=sum(1 for r in rows if r.selected),
        moments=[
            MomentOut(
                id=r.id,
                start_seconds=r.start_seconds,
                end_seconds=r.end_seconds,
                score=round(float(r.total_score)),
                selected=r.selected,
                rejected_reason=r.rejected_reason,
                why=r.rationale,
                hook_type=(
                    str((r.scores or {}).get("hook_type"))
                    if (r.scores or {}).get("hook_type") not in (None, "", "none")
                    else None
                ),
                transcript=(r.plan or {}).get("transcript"),
                can_promote=not r.selected and can_promote(r),
            )
            for r in rows
        ],
    )
