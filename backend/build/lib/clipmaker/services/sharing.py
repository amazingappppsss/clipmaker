"""Read-only results links: share a project's picked moments without an account."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.core.errors import NotFoundError
from clipmaker.db.models import Project
from clipmaker.schemas import SharedResultsOut
from clipmaker.services.processing import list_clips


def enable_sharing(db: Session, project: Project) -> str:
    """Return the project's share token, creating one if needed (idempotent)."""
    if not project.share_token:
        project.share_token = secrets.token_urlsafe(24)
        db.commit()
    return project.share_token


def disable_sharing(db: Session, project: Project) -> None:
    """Revoke the link: the old token stops working immediately."""
    project.share_token = None
    db.commit()


def shared_results(db: Session, token: str) -> SharedResultsOut:
    """The moments behind a share token. Video files are never exposed through a link."""
    project = db.scalar(
        select(Project).where(Project.share_token == token, Project.deleted_at.is_(None))
    )
    if project is None or len(token) < 16:
        raise NotFoundError("This link is invalid or has been turned off.")
    src = project.source_video
    return SharedResultsOut(
        title=project.title,
        state=project.state,
        source_url=src.source_url if src else None,
        duration_seconds=src.duration_seconds if src else None,
        clips=list_clips(db, project),
    )
