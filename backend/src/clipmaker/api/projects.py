"""Project and upload endpoints (PRD §10). Thin layer: validate → service → serialize."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status

from clipmaker.api.deps import AppSettings, CurrentUser, DbSession, Storage
from clipmaker.schemas import ProjectCreate, ProjectList, ProjectOut, UploadRequest, UploadTicket
from clipmaker.services import projects as project_service
from clipmaker.services import uploads as upload_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate, user: CurrentUser, db: DbSession, storage: Storage
) -> ProjectOut:
    """Create a project; upload its source video next."""
    project = project_service.create_project(db, user, body)
    return project_service.to_project_out(db, storage, project)


@router.get("")
def list_projects(
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    limit: int = Query(default=20, ge=1, le=project_service.MAX_PAGE_SIZE),
    cursor: str | None = None,
) -> ProjectList:
    """The user's projects, newest first."""
    rows, next_cursor = project_service.list_projects(db, user, limit, cursor)
    return ProjectList(
        items=[project_service.to_project_out(db, storage, p) for p in rows],
        next_cursor=next_cursor,
    )


@router.get("/{project_id}")
def get_project(
    project_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: Storage
) -> ProjectOut:
    """One project with its source-video metadata."""
    project = project_service.get_owned_project(db, user, project_id)
    return project_service.to_project_out(db, storage, project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_project(
    project_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: Storage
) -> None:
    """Permanently delete a project and all of its files."""
    project_service.delete_project(db, storage, user, project_id)


@router.post("/{project_id}/upload")
def request_upload(
    project_id: uuid.UUID,
    body: UploadRequest,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    settings: AppSettings,
) -> UploadTicket:
    """Issue a signed URL to upload the source video directly to storage."""
    project = project_service.get_owned_project(db, user, project_id)
    return upload_service.request_upload(db, storage, settings, project, body)


@router.post("/{project_id}/upload/complete")
def complete_upload(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    settings: AppSettings,
) -> ProjectOut:
    """Verify the uploaded file (exists, full size, readable video with audio)."""
    project = project_service.get_owned_project(db, user, project_id)
    upload_service.complete_upload(db, storage, settings, project)
    return project_service.to_project_out(db, storage, project)
