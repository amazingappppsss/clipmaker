"""INGESTING: preview thumbnail + speech-optimised audio track, both stored in object storage.

Idempotent: if both objects already exist they are reused.
"""

from __future__ import annotations

from clipmaker.db.models import SourceVideo
from clipmaker.media.audio import MediaError, extract_audio, make_thumbnail
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError


def run(ctx: StageContext) -> StageOutput:
    audio_key = f"{ctx.prefix}work/audio.mp3"
    thumb_key = f"{ctx.prefix}work/thumbnail.jpg"

    with ctx.sessions() as db:
        src = db.query(SourceVideo).filter_by(project_id=ctx.project_id).one_or_none()
        if src is None:
            raise PermanentStageError("no_source", "This project has no uploaded video.")
        source_key, duration = src.storage_key, float(src.duration_seconds or 0)

    if ctx.storage.head(audio_key) and ctx.storage.head(thumb_key):
        with ctx.sessions() as db:
            db.query(SourceVideo).filter_by(project_id=ctx.project_id).update(
                {"thumbnail_key": thumb_key}
            )
            db.commit()
        return StageOutput({"audio_key": audio_key, "thumbnail_key": thumb_key}, skipped=True)

    media = ctx.storage.media_source(source_key)
    try:
        thumb = make_thumbnail(
            media, ctx.work_dir / "thumbnail.jpg", at_seconds=min(5.0, duration / 3)
        )
        audio = extract_audio(media, ctx.work_dir / "audio.mp3")
    except MediaError as exc:
        # A file that passed upload verification but cannot be decoded is not going to improve.
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
    return StageOutput({"audio_key": audio_key, "thumbnail_key": thumb_key})
