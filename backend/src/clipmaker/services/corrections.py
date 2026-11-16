"""Correcting a clip the AI got wrong.

The product's real gap is not a missing feature — it is that a wrong decision cannot be fixed.
Framing drifts, a cut lands before the laugh, a name is captioned wrong, and the clip is simply
unusable with no recourse. This is the machinery behind undoing that.

How a correction replays:

* The human's change is stored on `Clip.corrections`, separately from `edit_plan`. The AI's
  plan is regenerated from scratch each time; the correction has to survive that, so the two
  never share a home.
* The stored render plan is dropped and the clip's video assets are deleted, which is exactly
  what EDITING and RENDERING look at to decide whether a clip still needs work. Both stages
  are idempotent, so the project is simply re-run and only this clip is touched.
* Nothing is charged. The viewer already paid to process this video, and making us fix our own
  bad cut at their expense would be a tax on our mistakes.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.enums import AssetKind, ClipStatus, ProjectState
from clipmaker.core.errors import ConflictError, NotFoundError
from clipmaker.db.models import Clip, ProcessingJob, Project
from clipmaker.storage.base import ObjectStorage

logger = logging.getLogger(__name__)

#: Stages that have to run again for a corrected clip. Everything before EDITING — the
#: download, the transcript, the AI's choice of moments — is unaffected and is kept.
REPLAY_STAGES = ("EDITING", "RENDERING", "QUALITY_CHECK")

#: A project has to be settled before a clip can be corrected; mid-run, the pipeline owns it.
_CORRECTABLE = (ProjectState.COMPLETED, ProjectState.NEEDS_REVIEW, ProjectState.FAILED)


def get_clip(db: Session, project: Project, clip_id: uuid.UUID) -> Clip:
    """One clip of this project, or 404. Scoped by project so ids can't be fished for."""
    clip = db.scalar(select(Clip).where(Clip.id == clip_id, Clip.project_id == project.id))
    if clip is None:
        raise NotFoundError("Clip not found")
    return clip


def correct(
    db: Session,
    project: Project,
    clip: Clip,
    changes: dict[str, Any],
    storage: ObjectStorage,
) -> ProcessingJob:
    """Store a correction and queue this one clip to be rebuilt.

    Raises:
        ConflictError: the project is still being processed.
    """
    if project.state not in _CORRECTABLE:
        raise ConflictError("Wait for this video to finish before changing a clip.")
    if not changes:
        raise ConflictError("Nothing to change.")

    clip.corrections = {**(clip.corrections or {}), **changes}
    # Drop the AI's plan so EDITING rebuilds it with the correction applied. The rest of
    # `edit_plan` (the picked moment, the transcript) is what the correction is relative to,
    # so it stays.
    clip.edit_plan = {k: v for k, v in (clip.edit_plan or {}).items() if k != "render"}
    clip.status = ClipStatus.PLANNED
    clip.attempts = 0
    clip.error_message = None

    # RENDERING skips clips that already have a video, so the old one has to go. The file is
    # deleted too: keeping it would quietly fill a disk that is already the tightest resource
    # we have.
    for asset in list(clip.assets):
        if asset.kind == AssetKind.VIDEO:
            try:
                storage.delete_prefix(asset.storage_key)
            except Exception:  # a storage hiccup must not block the correction
                logger.warning("correction_asset_delete_failed", extra={"clip_id": str(clip.id)})
            db.delete(asset)

    job = db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.project_id == project.id)
        .order_by(ProcessingJob.created_at.desc())
    )
    if job is None:
        job = ProcessingJob(project_id=project.id, state=ProjectState.EDITING, stages={})
        db.add(job)
    else:
        # Keep the expensive stages that are already done; replay only from EDITING.
        job.stages = {k: v for k, v in (job.stages or {}).items() if k not in REPLAY_STAGES}
        job.state = ProjectState.EDITING
        job.error_code = job.error_detail = None
        job.completed_at = None

    project.state = ProjectState.EDITING
    project.error_message = None
    db.commit()
    db.refresh(job)
    logger.info(
        "clip_corrected",
        extra={"clip_id": str(clip.id), "fields": sorted(changes)},
    )
    return job
