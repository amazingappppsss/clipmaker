"""Project lifecycle: create, list, read, delete — always scoped to the owning user."""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from clipmaker.core.enums import UploadStatus
from clipmaker.core.errors import NotFoundError, ValidationFailedError
from clipmaker.db.models import Clip, Project, User
from clipmaker.schemas import ProjectCreate, ProjectOut, ProjectSettings, SourceVideoOut
from clipmaker.storage.base import ObjectStorage, project_prefix

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 50


def create_project(db: Session, user: User, body: ProjectCreate) -> Project:
    """Create an empty project awaiting its source video."""
    project = Project(user_id=user.id, title=body.title, settings=body.settings.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("project_created", extra={"project_id": str(project.id), "user_id": str(user.id)})
    return project


def get_owned_project(db: Session, user: User, project_id: uuid.UUID) -> Project:
    """Load a project the user owns. Another user's project is reported as not found."""
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.source_video))
        .where(
            Project.id == project_id,
            Project.user_id == user.id,
            Project.deleted_at.is_(None),
        )
    )
    if project is None:
        raise NotFoundError("Project not found")
    return project


def _encode_cursor(created_at: datetime, project_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{project_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        ts, _, pid = base64.urlsafe_b64decode(cursor.encode()).decode().partition("|")
        return datetime.fromisoformat(ts), uuid.UUID(pid)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValidationFailedError("Invalid cursor") from exc


def list_projects(
    db: Session, user: User, limit: int, cursor: str | None
) -> tuple[list[Project], str | None]:
    """Newest-first keyset pagination (stable under concurrent inserts)."""
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    query = (
        select(Project)
        .options(selectinload(Project.source_video))
        .where(Project.user_id == user.id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc(), Project.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        ts, pid = _decode_cursor(cursor)
        query = query.where(
            or_(Project.created_at < ts, and_(Project.created_at == ts, Project.id < pid))
        )
    rows = list(db.scalars(query))
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id)
    return rows, next_cursor


def delete_project(db: Session, storage: ObjectStorage, user: User, project_id: uuid.UUID) -> None:
    """Delete a project and every stored file belonging to it (PRD §12 proper deletion).

    Storage is purged first: if that fails the DB row survives and the user can retry,
    so we never end up with orphaned private videos nobody can delete.
    """
    project = get_owned_project(db, user, project_id)
    removed = storage.delete_prefix(project_prefix(str(user.id), str(project.id)))
    db.delete(project)
    db.commit()
    logger.info("project_deleted", extra={"project_id": str(project_id), "objects": removed})


def to_project_out(db: Session, storage: ObjectStorage, project: Project) -> ProjectOut:
    """Serialize a project, attaching a short-lived thumbnail URL when one exists."""
    src = project.source_video
    clip_count = db.scalar(select(func.count()).where(Clip.project_id == project.id)) or 0
    return ProjectOut(
        id=project.id,
        title=project.title,
        state=project.state,
        settings=ProjectSettings.model_validate(project.settings),
        error_message=project.error_message,
        created_at=project.created_at,
        updated_at=project.updated_at,
        source_video=SourceVideoOut.model_validate(src) if src else None,
        thumbnail_url=(
            storage.presign_download(src.thumbnail_key) if src and src.thumbnail_key else None
        ),
        source_video_url=(
            storage.presign_download(src.storage_key)
            if src
            and src.upload_status == UploadStatus.VERIFIED
            and storage.head(src.storage_key) is not None  # freed after clips were rendered
            else None
        ),
        clip_count=clip_count,
    )
