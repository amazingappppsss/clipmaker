"""INGESTING: make sure the source video is in storage, then build a thumbnail and the
speech-optimised audio track.

* Uploaded videos are already in storage (verified at upload time).
* Link imports (e.g. YouTube) are downloaded here, in the worker — never in an API request —
  then verified with ffprobe exactly like an upload before anything else runs.

Idempotent: a downloaded source, thumbnail and audio already in storage are reused.
"""

from __future__ import annotations

from typing import Any

from clipmaker.core.enums import UploadStatus
from clipmaker.core.errors import InsufficientCreditsError
from clipmaker.db.models import Project, SourceVideo, User
from clipmaker.media.audio import MediaError, extract_audio, make_streamable, make_thumbnail
from clipmaker.media.probe import ProbeError, probe_media
from clipmaker.media.url_import import UrlImportError
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError
from clipmaker.services.billing import credits_for_duration, debit_credits, project_net_charge

_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}


def _fetch_from_link(ctx: StageContext, src: SourceVideo) -> dict[str, Any]:
    """Download a link import into storage and verify it. Returns fields to save on the row."""
    if not src.source_url:
        raise PermanentStageError("no_source", "This project has no video link.")
    try:
        path = ctx.importer().download(src.source_url, ctx.work_dir / "download", ctx.heartbeat)
    except UrlImportError as exc:
        error = RetryableStageError if exc.retryable else PermanentStageError
        raise error(exc.code, exc.message) from exc

    try:
        meta = probe_media(str(path))
    except ProbeError as exc:
        raise PermanentStageError(
            "unreadable_video", f"The downloaded video is unreadable: {exc}"
        ) from exc
    if not meta.has_audio:
        raise PermanentStageError(
            "no_audio", "This video has no audio track, so there is nothing to transcribe."
        )
    limits = ctx.settings
    if meta.duration_seconds < limits.min_video_duration_seconds:
        raise PermanentStageError(
            "too_short", f"Video is too short (minimum {limits.min_video_duration_seconds} s)."
        )
    if meta.duration_seconds > limits.max_video_duration_seconds:
        raise PermanentStageError(
            "too_long",
            f"Video is too long (maximum {limits.max_video_duration_seconds // 60} min).",
        )

    if path.suffix in (".mp4", ".mov"):
        # Downloaded MP4s often keep their index at the end, which makes previews spin until
        # the whole file loads. A quick lossless remux fixes that; the original is fine if not.
        try:
            path = make_streamable(path, path.with_name(f"streamable{path.suffix}"))
        except MediaError:
            pass

    key = src.storage_key.rsplit(".", 1)[0] + path.suffix
    try:
        info = ctx.storage.upload_file(path, key, _CONTENT_TYPES.get(path.suffix, "video/mp4"))
    except OSError as exc:
        raise RetryableStageError("storage_error", "Saving the downloaded video failed.") from exc
    return {
        "storage_key": key,
        "size_bytes": info.size_bytes,
        "content_type": _CONTENT_TYPES.get(path.suffix, "video/mp4"),
        "duration_seconds": meta.duration_seconds,
        "width": meta.width,
        "height": meta.height,
        "fps": meta.fps,
        "video_codec": meta.video_codec,
        "has_audio": meta.has_audio,
        "probe": meta.raw,
        "upload_status": UploadStatus.VERIFIED,
        "error_message": None,
    }


def _charge_if_not_charged(db: Any, ctx: StageContext, duration: float) -> None:
    """Link imports with an unknown length are charged here, once, for the measured length."""
    if project_net_charge(db, ctx.project_id) > 0:
        return
    user = db.get(User, ctx.user_id)
    project = db.get(Project, ctx.project_id)
    if user is None or project is None:
        raise PermanentStageError("no_source", "This project no longer exists.")
    try:
        debit_credits(
            db,
            user,
            credits_for_duration(duration),
            ctx.project_id,
            f"Processing: {project.title[:120]}",
        )
    except InsufficientCreditsError as exc:
        raise PermanentStageError("insufficient_credits", exc.message) from exc


def run(ctx: StageContext) -> StageOutput:
    audio_key = f"{ctx.prefix}work/audio.mp3"
    thumb_key = f"{ctx.prefix}work/thumbnail.jpg"
    outputs: dict[str, Any] = {}

    with ctx.sessions() as db:
        src = db.query(SourceVideo).filter_by(project_id=ctx.project_id).one_or_none()
        if src is None:
            raise PermanentStageError("no_source", "This project has no video.")
        needs_download = src.source_kind == "url" and src.upload_status != UploadStatus.VERIFIED
        if needs_download:
            updates = _fetch_from_link(ctx, src)
            for field, value in updates.items():
                setattr(src, field, value)
            _charge_if_not_charged(db, ctx, float(updates["duration_seconds"]))
            db.commit()
            outputs["downloaded_bytes"] = updates["size_bytes"]
        source_key, duration = src.storage_key, float(src.duration_seconds or 0)

    if ctx.storage.head(audio_key) and ctx.storage.head(thumb_key):
        with ctx.sessions() as db:
            db.query(SourceVideo).filter_by(project_id=ctx.project_id).update(
                {"thumbnail_key": thumb_key}
            )
            db.commit()
        return StageOutput(
            {**outputs, "audio_key": audio_key, "thumbnail_key": thumb_key}, skipped=True
        )

    media = ctx.storage.media_source(source_key)
    try:
        thumb = make_thumbnail(
            media, ctx.work_dir / "thumbnail.jpg", at_seconds=min(5.0, duration / 3)
        )
        audio = extract_audio(media, ctx.work_dir / "audio.mp3")
    except MediaError as exc:
        # A file that passed verification but cannot be decoded is not going to improve.
        raise PermanentStageError("media_unreadable", f"We couldn't read the video: {exc}") from exc

    try:
        ctx.storage.upload_file(thumb, thumb_key, "image/jpeg")
        ctx.storage.upload_file(audio, audio_key, "audio/mpeg")
    except OSError as exc:
        raise RetryableStageError("storage_error", "Saving processed files failed.") from exc

    with ctx.sessions() as db:
        db.query(SourceVideo).filter_by(project_id=ctx.project_id).update(
            {"thumbnail_key": thumb_key}
        )
        db.commit()
    return StageOutput({**outputs, "audio_key": audio_key, "thumbnail_key": thumb_key})
