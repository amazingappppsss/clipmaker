"""Direct-to-storage uploads with server-side verification (PRD §5.1).

Flow:
1. `request_upload`   — validate the declared file, issue a signed PUT URL.
2. browser PUTs the bytes straight to storage (progress is tracked client-side).
3. `complete_upload`  — confirm the object exists with the declared size, probe it with
   ffprobe, enforce duration/stream rules, then mark the project UPLOADED.
A project is never marked uploaded on the client's word alone.

TECH DEBT: single-PUT uploads cap at 5 GiB and are not resumable. Add S3 multipart
presigned parts for resumable uploads (tracked in TASKS.md).
"""

from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from clipmaker.core.config import Settings
from clipmaker.core.enums import ProjectState, UploadStatus
from clipmaker.core.errors import ConflictError, ValidationFailedError
from clipmaker.db.models import Project, SourceVideo
from clipmaker.media.probe import ProbeError, probe_media
from clipmaker.schemas import ALLOWED_VIDEO_TYPES, UploadRequest, UploadTicket
from clipmaker.storage.base import ObjectStorage, project_prefix

logger = logging.getLogger(__name__)

_UPLOADABLE_STATES = {ProjectState.CREATED, ProjectState.UPLOADED}
_EXTENSION_ALIASES = {".m4v": ".mp4", ".qt": ".mov"}


def _human_minutes(seconds: float) -> str:
    return f"{seconds / 60:.0f} min" if seconds >= 60 else f"{seconds:.0f} s"


def validate_upload_request(body: UploadRequest, settings: Settings) -> str:
    """Check type, extension and size; return the canonical file extension.

    Raises:
        ValidationFailedError: with a user-readable explanation.
    """
    expected_ext = ALLOWED_VIDEO_TYPES.get(body.content_type)
    if expected_ext is None:
        raise ValidationFailedError(
            "Unsupported file type. Upload an MP4, MOV, WebM or MKV video.", code="unsupported_type"
        )
    ext = os.path.splitext(body.filename)[1].lower()
    ext = _EXTENSION_ALIASES.get(ext, ext)
    if ext != expected_ext:
        raise ValidationFailedError(
            "The file extension does not match its type.", code="extension_mismatch"
        )
    if body.size_bytes > settings.max_upload_bytes:
        limit_gb = settings.max_upload_bytes / 1024**3
        raise ValidationFailedError(f"File is larger than {limit_gb:.0f} GB.", code="too_large")
    return expected_ext


def request_upload(
    db: Session, storage: ObjectStorage, settings: Settings, project: Project, body: UploadRequest
) -> UploadTicket:
    """Register the intended upload and return signed PUT instructions."""
    if project.state not in _UPLOADABLE_STATES:
        raise ConflictError("This project is already being processed.")
    ext = validate_upload_request(body, settings)
    key = f"{project_prefix(str(project.user_id), str(project.id))}source/original{ext}"

    src = project.source_video
    if src is None:
        src = SourceVideo(
            project_id=project.id,
            storage_key=key,
            original_filename="",
            size_bytes=0,
            content_type=body.content_type,
        )
        db.add(src)
    src.storage_key = key
    src.original_filename = body.filename
    src.content_type = body.content_type
    src.size_bytes = body.size_bytes
    src.upload_status = UploadStatus.PENDING
    src.error_message = None
    project.state = ProjectState.CREATED
    db.commit()

    signed = storage.presign_upload(key, body.content_type, body.size_bytes)
    return UploadTicket(
        upload_url=signed.url,
        method=signed.method,
        headers=signed.headers,
        expires_in=signed.expires_in,
    )


def _fail(db: Session, src: SourceVideo, message: str, code: str) -> ValidationFailedError:
    src.upload_status = UploadStatus.FAILED
    src.error_message = message
    db.commit()
    logger.warning("upload_rejected", extra={"project_id": str(src.project_id), "reason": code})
    return ValidationFailedError(message, code=code)


def complete_upload(
    db: Session, storage: ObjectStorage, settings: Settings, project: Project
) -> SourceVideo:
    """Verify the uploaded object and record its metadata.

    Raises:
        ConflictError: if no upload was requested.
        ValidationFailedError: if the object is missing, truncated or not an acceptable video.
    """
    src = project.source_video
    if src is None or project.state not in _UPLOADABLE_STATES:
        raise ConflictError("No pending upload for this project.")

    info = storage.head(src.storage_key)
    if info is None:
        raise _fail(db, src, "Upload not found. Please try uploading again.", "upload_missing")
    if info.size_bytes != src.size_bytes:
        raise _fail(db, src, "Upload was incomplete. Please try again.", "upload_incomplete")

    try:
        meta = probe_media(storage.media_source(src.storage_key))
    except ProbeError as exc:
        raise _fail(db, src, f"We couldn't read this video ({exc}).", "unreadable_video") from exc

    if not meta.has_audio:
        raise _fail(
            db, src, "This video has no audio track, so there is nothing to transcribe.", "no_audio"
        )
    if meta.duration_seconds < settings.min_video_duration_seconds:
        raise _fail(
            db,
            src,
            f"Video is too short (minimum {_human_minutes(settings.min_video_duration_seconds)}).",
            "too_short",
        )
    if meta.duration_seconds > settings.max_video_duration_seconds:
        raise _fail(
            db,
            src,
            f"Video is too long (maximum {_human_minutes(settings.max_video_duration_seconds)}).",
            "too_long",
        )

    src.duration_seconds = meta.duration_seconds
    src.width, src.height, src.fps = meta.width, meta.height, meta.fps
    src.video_codec = meta.video_codec
    src.has_audio = meta.has_audio
    src.probe = meta.raw
    src.upload_status = UploadStatus.VERIFIED
    src.error_message = None
    project.state = ProjectState.UPLOADED
    db.commit()
    logger.info(
        "upload_verified",
        extra={"project_id": str(project.id), "duration_s": meta.duration_seconds},
    )
    return src
