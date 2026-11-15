"""Keeping the disk usable on a small host.

A video host fills its disk eventually: every import lands a file, and finished projects keep
their clips. Rather than fail a download with "no space left", we make room first by deleting
the media of the oldest finished projects. Their rows stay, so the project is still listed and
can be run again; only the files go.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.enums import ProjectState
from clipmaker.db.models import Clip, ClipAsset, Project
from clipmaker.storage.base import ObjectStorage, project_prefix

logger = logging.getLogger(__name__)

# Keep this much free after making room, so the next step has somewhere to work.
HEADROOM_BYTES = 300 * 1024 * 1024
# Never touch a project that is still running or waiting to be looked at.
REMOVABLE = (ProjectState.COMPLETED, ProjectState.FAILED, ProjectState.CANCELLED)


def free_bytes(path: str) -> int | None:
    """Free bytes where media is stored, or None when storage isn't a local disk."""
    try:
        target = path if Path(path).exists() else str(Path(path).parent or "/")
        return shutil.disk_usage(target).free
    except OSError:
        return None


def make_room(db: Session, storage: ObjectStorage, local_dir: str | None, needed_bytes: int) -> int:
    """Delete old finished projects' media until `needed_bytes` fits. Returns files removed.

    Cloud storage (R2/S3) has no local limit, so nothing is deleted there.
    """
    if not local_dir:
        return 0
    free = free_bytes(local_dir)
    if free is None or free >= needed_bytes + HEADROOM_BYTES:
        return 0

    removed = 0
    projects = db.scalars(
        select(Project)
        .where(Project.state.in_(REMOVABLE), Project.deleted_at.is_(None))
        .order_by(Project.updated_at.asc())
    ).all()
    for project in projects:
        prefix = project_prefix(str(project.user_id), str(project.id))
        try:
            removed += storage.delete_prefix(prefix)
        except OSError:
            continue
        # The files are gone: stop offering them for download.
        clip_ids = db.scalars(select(Clip.id).where(Clip.project_id == project.id)).all()
        if clip_ids:
            for asset in db.scalars(select(ClipAsset).where(ClipAsset.clip_id.in_(clip_ids))).all():
                db.delete(asset)
        db.commit()
        logger.info("freed_project_media", extra={"project_id": str(project.id), "files": removed})
        free = free_bytes(local_dir) or 0
        if free >= needed_bytes + HEADROOM_BYTES:
            break
    return removed
