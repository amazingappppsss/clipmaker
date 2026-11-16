"""Project and upload endpoints (PRD §10). Thin layer: validate → service → serialize."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status

from clipmaker.api.deps import AppSettings, CurrentUser, DbSession, Importer, JobQueue, Storage
from clipmaker.schemas import (
    ClipCorrectionIn,
    ClipOut,
    ImportRequest,
    JobStatusOut,
    ProjectCreate,
    ProjectList,
    ProjectOut,
    SharedResultsOut,
    ShareLinkOut,
    UploadRequest,
    UploadTicket,
)
from clipmaker.services import corrections as corrections_service
from clipmaker.services import imports as import_service
from clipmaker.services import processing as processing_service
from clipmaker.services import projects as project_service
from clipmaker.services import sharing
from clipmaker.services import uploads as upload_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate, user: CurrentUser, db: DbSession, storage: Storage
) -> ProjectOut:
    """Create a project; upload its source video next."""
    project = project_service.create_project(db, user, body)
    return project_service.to_project_out(db, storage, project)


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_project(
    body: ImportRequest,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    settings: AppSettings,
    importer: Importer,
) -> ProjectOut:
    """Create a project from a video link (e.g. YouTube). The download runs in the worker."""
    project = import_service.import_from_url(db, settings, importer, user, body)
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


@router.post("/{project_id}/process", status_code=status.HTTP_202_ACCEPTED)
def start_processing(
    project_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: Storage, enqueue: JobQueue
) -> ProjectOut:
    """Charge credits and start (or retry) the clipping pipeline in the background."""
    project = project_service.get_owned_project(db, user, project_id)
    processing_service.start_processing(db, user, project, enqueue)
    return project_service.to_project_out(db, storage, project)


@router.post("/{project_id}/cancel")
def cancel_processing(
    project_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: Storage
) -> ProjectOut:
    """Stop processing and refund its credits. Completed steps are kept for a later retry."""
    project = project_service.get_owned_project(db, user, project_id)
    processing_service.cancel_processing(db, project)
    return project_service.to_project_out(db, storage, project)


@router.get("/{project_id}/status")
def get_status(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> JobStatusOut:
    """Per-stage processing status."""
    project = project_service.get_owned_project(db, user, project_id)
    return processing_service.job_status(db, project)


@router.get("/{project_id}/clips")
def get_clips(
    project_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: Storage
) -> list[ClipOut]:
    """Selected clips for the project, best first, with links to the finished videos."""
    project = project_service.get_owned_project(db, user, project_id)
    return processing_service.list_clips(db, project, storage)


@router.patch("/{project_id}/clips/{clip_id}", status_code=status.HTTP_202_ACCEPTED)
def correct_clip(
    project_id: uuid.UUID,
    clip_id: uuid.UUID,
    payload: ClipCorrectionIn,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    queue: JobQueue,
) -> dict[str, str]:
    """Fix a clip the AI got wrong, and rebuild just that one.

    Not charged: the viewer already paid to process this video, and billing them to correct
    our own bad cut would be a tax on our mistakes.
    """
    project = project_service.get_owned_project(db, user, project_id)
    clip = corrections_service.get_clip(db, project, clip_id)
    job = corrections_service.correct(db, project, clip, payload.changes(), storage)
    queue(job.id)
    return {"status": "rebuilding"}


@router.post("/{project_id}/share")
def share_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ShareLinkOut:
    """Create (or return) a read-only link to this project's picked moments."""
    project = project_service.get_owned_project(db, user, project_id)
    return ShareLinkOut(token=sharing.enable_sharing(db, project))


@router.delete(
    "/{project_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def unshare_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Turn the read-only link off."""
    sharing.disable_sharing(db, project_service.get_owned_project(db, user, project_id))


shared_router = APIRouter(prefix="/share", tags=["sharing"])


@shared_router.get("/{token}")
def get_shared(token: str, db: DbSession) -> SharedResultsOut:
    """Public, read-only: the moments behind a share link."""
    return sharing.shared_results(db, token)
