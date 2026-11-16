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
#: Never ask for more than this share of the disk. A request that cannot be satisfied makes
#: the loop delete everything it is allowed to and still "fail" — which is what happened on a
#: 0.45 GB volume asked to free 500 MB: every sweep wiped every removable project, forever.
MAX_SHARE_OF_DISK = 0.6
# Never touch a project that is still running or waiting to be looked at.
REMOVABLE = (ProjectState.COMPLETED, ProjectState.FAILED, ProjectState.CANCELLED)
#: Deleted last. A failed project is the one most likely to be run again, and without its
#: source "Try again" can only fail — which is a worse outcome than a full disk.
LAST_RESORT = ProjectState.FAILED


def disk_total(path: str) -> int | None:
    """Total bytes of the disk holding `path`, or None when it isn't a local disk."""
    try:
        target = path if Path(path).exists() else str(Path(path).parent or "/")
        return shutil.disk_usage(target).total
    except OSError:
        return None


def affordable(needed_bytes: int, local_dir: str) -> int:
    """`needed_bytes`, clamped to something this disk could actually provide (pure enough).

    Asking for more than the disk holds is not a stricter request, it is an unsatisfiable
    one: the loop then deletes every project it may touch and still comes up short.
    """
    total = disk_total(local_dir)
    if total is None:
        return needed_bytes
    ceiling = int(total * MAX_SHARE_OF_DISK) - HEADROOM_BYTES
    return max(0, min(needed_bytes, ceiling))


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
    needed_bytes = affordable(needed_bytes, local_dir)
    free = free_bytes(local_dir)
    if free is None or needed_bytes <= 0 or free >= needed_bytes + HEADROOM_BYTES:
        return 0

    removed = 0
    rows = db.scalars(
        select(Project)
        .where(Project.state.in_(REMOVABLE), Project.deleted_at.is_(None))
        .order_by(Project.updated_at.asc())
    ).all()
    # Oldest first, but failed projects last: their source is what "Try again" needs.
    projects = [p for p in rows if p.state != LAST_RESORT] + [
        p for p in rows if p.state == LAST_RESORT
    ]
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
