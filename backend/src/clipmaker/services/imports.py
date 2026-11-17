"""Create a project from a link (e.g. YouTube).

The API request only *inspects* the link (title + duration, a few seconds) so the user sees
errors immediately and credits can be priced. The actual download happens in the worker's
INGESTING stage — never inside an API request.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from clipmaker.core.config import Settings
from clipmaker.core.enums import ProjectState, UploadStatus
from clipmaker.core.errors import AppError, ValidationFailedError
from clipmaker.db.models import Project, SourceVideo, User
from clipmaker.media.budget import import_height, too_long_message
from clipmaker.media.url_import import UrlImporter, UrlImportError, validate_url
from clipmaker.schemas import ImportRequest
from clipmaker.services.housekeeping import budget_bytes
from clipmaker.storage.base import project_prefix

logger = logging.getLogger(__name__)


class FeatureDisabledError(AppError):
    """Link import switched off by configuration."""

    status_code = 403
    code = "url_import_disabled"


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.0f} min" if seconds >= 60 else f"{seconds:.0f} s"


def import_from_url(
    db: Session, settings: Settings, importer: UrlImporter, user: User, body: ImportRequest
) -> Project:
    """Validate the link, read its metadata and create a project ready to process.

    Raises:
        FeatureDisabledError: link import is turned off.
        ValidationFailedError: rights not confirmed, bad link, unavailable/too long/live video.
    """
    if not settings.enable_url_import:
        raise FeatureDisabledError("Importing from links is turned off. Please upload a file.")
    if not body.rights_confirmed:
        raise ValidationFailedError(
            "Please confirm you own this video or have permission to use it.",
            code="rights_not_confirmed",
        )
    try:
        url = validate_url(body.url)
        remote = importer.inspect(url)
    except UrlImportError as exc:
        raise ValidationFailedError(exc.message, code=exc.code) from exc

    if remote.is_live:
        raise ValidationFailedError(
            "Live streams can't be imported. Try again after it ends.", code="source_live"
        )
    # Some download services don't report a length; then the worker measures it after the
    # download (and checks limits + charges credits there) instead of rejecting the link.
    known = remote.duration_seconds > 0
    if known and remote.duration_seconds < settings.min_video_duration_seconds:
        raise ValidationFailedError(
            f"Video is too short (minimum {_minutes(settings.min_video_duration_seconds)}).",
            code="too_short",
        )
    if known and remote.duration_seconds > settings.max_video_duration_seconds:
        raise ValidationFailedError(
            f"Video is too long (maximum {_minutes(settings.max_video_duration_seconds)}).",
            code="too_long",
        )
    # Refuse here, while they are still watching, rather than in the worker halfway through a
    # download that cannot fit on the disk. The worker checks again with its own disk.
    if known and settings.storage_backend.value == "local":
        budget = budget_bytes(settings.local_storage_dir)
        if import_height(remote.duration_seconds, budget, settings.url_import_max_height) is None:
            raise ValidationFailedError(
                too_long_message(remote.duration_seconds, budget), code="too_long_to_download"
            )

    project = Project(
        user_id=user.id,
        title=body.title or remote.title,
        settings=body.settings.model_dump(),
        state=ProjectState.UPLOADED,
    )
    db.add(project)
    db.flush()
    project.source_video = SourceVideo(
        project_id=project.id,
        storage_key=f"{project_prefix(str(user.id), str(project.id))}source/original.mp4",
        source_kind="url",
        source_url=remote.url,
        original_filename=f"{remote.title[:180]}.mp4",
        content_type="video/mp4",
        size_bytes=0,  # known after the worker downloads it
        upload_status=UploadStatus.PENDING,
        duration_seconds=remote.duration_seconds if known else None,
    )
    db.commit()
    db.refresh(project)
    logger.info(
        "project_imported",
        extra={"project_id": str(project.id), "duration_s": remote.duration_seconds},
    )
    return project
