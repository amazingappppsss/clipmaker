"""Starting/retrying processing and reporting status.

Credits are debited when processing starts and refunded automatically if the job fails
(pipeline/runner.py). A failed project can be retried: completed stages are kept, only the
failed stage onward runs again.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.enums import PIPELINE_STAGES, TERMINAL_STATES, ProjectState
from clipmaker.core.errors import ConflictError
from clipmaker.db.models import Candidate, Clip, ProcessingJob, Project, User
from clipmaker.pipeline.selection import strengths
from clipmaker.schemas import ClipOut, JobStatusOut, StageStatusOut
from clipmaker.services.billing import credits_for_duration, debit_credits

logger = logging.getLogger(__name__)

Enqueue = Callable[[uuid.UUID], None]

_STARTABLE = {ProjectState.UPLOADED, ProjectState.FAILED}


def latest_job(db: Session, project_id: uuid.UUID) -> ProcessingJob | None:
    return db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.project_id == project_id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )


def start_processing(db: Session, user: User, project: Project, enqueue: Enqueue) -> ProcessingJob:
    """Charge credits and queue the pipeline. Retrying a failed project resumes its last job.

    Raises:
        ConflictError: the project is not in a startable state.
        InsufficientCreditsError: not enough credits.
    """
    if project.state not in _STARTABLE:
        raise ConflictError(
            "Upload a video first."
            if project.state == ProjectState.CREATED
            else "This project is already processing or finished."
        )
    src = project.source_video
    if src is None or (src.duration_seconds is None and src.source_kind != "url"):
        raise ConflictError("Upload a video first.")

    # Length known → charge now. A link whose length is unknown is charged by the worker once the
    # download has been measured (pipeline/stages/ingest.py), so users pay for the real length.
    credits = 0  # deferred: charged after download for links with an unknown length
    if src.duration_seconds is not None:
        credits = credits_for_duration(src.duration_seconds)
        debit_credits(db, user, credits, project.id, f"Processing: {project.title[:120]}")

    job = latest_job(db, project.id) if project.state == ProjectState.FAILED else None
    if job is None:
        job = ProcessingJob(project_id=project.id, state=ProjectState.INGESTING, stages={})
        db.add(job)
    else:
        # Keep completed stages; reset only the failed one so it gets fresh attempts.
        job.stages = {k: v for k, v in job.stages.items() if v.get("status") == "done"}
        job.state = ProjectState.INGESTING
        job.error_code = job.error_detail = None
        job.completed_at = None
    project.state = ProjectState.INGESTING
    project.error_message = None
    db.commit()
    db.refresh(job)
    enqueue(job.id)
    logger.info(
        "processing_started",
        extra={"project_id": str(project.id), "job_id": str(job.id), "credits": credits},
    )
    return job


def job_status(db: Session, project: Project) -> JobStatusOut:
    """Real per-stage status for the processing page (never simulated)."""
    job = latest_job(db, project.id)
    stages: list[StageStatusOut] = []
    for stage in PIPELINE_STAGES:
        rec = (job.stages.get(stage.value, {}) if job else {}) or {}
        stages.append(
            StageStatusOut(
                stage=stage,
                status=rec.get("status", "pending"),
                attempts=int(rec.get("attempts", 0)),
            )
        )
    return JobStatusOut(
        project_state=project.state,
        progress=job.progress if job else 0.0,
        stages=stages,
        message=project.error_message,
        error_code=job.error_code if job and project.state == ProjectState.FAILED else None,
        started_at=job.started_at if job else None,
        completed_at=job.completed_at if job else None,
    )


def list_clips(db: Session, project: Project) -> list[ClipOut]:
    clips = db.scalars(select(Clip).where(Clip.project_id == project.id).order_by(Clip.rank)).all()
    out = []
    for c in clips:
        plan = c.edit_plan or {}
        cand = db.get(Candidate, c.candidate_id) if c.candidate_id else None
        scores: dict[str, Any] = dict(cand.scores or {}) if cand else {}
        story = scores.get("story") if isinstance(scores.get("story"), dict) else {}
        numeric = {k: float(v) for k, v in scores.items() if isinstance(v, int | float)}
        teaser = plan.get("teaser") if isinstance(plan.get("teaser"), dict) else None
        out.append(
            ClipOut(
                id=c.id,
                rank=c.rank,
                status=c.status,
                title=c.title,
                hook=c.hook,
                alt_titles=c.alt_titles,
                social_caption=c.social_caption,
                hashtags=c.hashtags,
                duration_seconds=c.duration_seconds,
                start_seconds=plan.get("start"),
                end_seconds=plan.get("end"),
                transcript=plan.get("transcript"),
                score=round(float(cand.total_score)) if cand and cand.total_score else None,
                why=(cand.rationale or None) if cand else None,
                strengths=strengths(numeric),
                five_second_moment=(story or {}).get("five_second_moment") or None,
                teaser_text=teaser.get("text") if teaser else None,
                teaser_start_seconds=teaser.get("start") if teaser else None,
                teaser_end_seconds=teaser.get("end") if teaser else None,
            )
        )
    return out


def stale_job_ids(db: Session, stale_after: timedelta) -> list[uuid.UUID]:
    """Non-terminal jobs whose worker vanished (lease expired, or never leased for a while)."""
    now = datetime.now(UTC)
    rows = db.scalars(
        select(ProcessingJob.id).where(
            ProcessingJob.state.notin_(TERMINAL_STATES),
            ((ProcessingJob.lease_expires_at.is_not(None)) & (ProcessingJob.lease_expires_at < now))
            | (
                (ProcessingJob.lease_owner.is_(None))
                & (ProcessingJob.updated_at < now - stale_after)
            ),
        )
    ).all()
    return list(rows)
