"""RENDERING: produce each clip's finished vertical MP4 (and a thumbnail) and store them.

Idempotent: a clip that already has a rendered video is skipped. One clip failing to render
doesn't sink the others; the stage fails only if no clip could be rendered.
"""

from __future__ import annotations

import logging
from typing import Any

from clipmaker.core.enums import AssetKind, ClipStatus
from clipmaker.db.models import Clip, ClipAsset, SourceVideo
from clipmaker.editing.captions import build_ass
from clipmaker.editing.framing import Shot, crop_box
from clipmaker.editing.render import CaptionsFor, Piece, render
from clipmaker.media.audio import MediaError, make_thumbnail
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError
from clipmaker.pipeline.stages.common import local_source
from clipmaker.pipeline.stages.qa import verify
from clipmaker.providers.transcription.base import Word

logger = logging.getLogger(__name__)

MAX_CLIP_ATTEMPTS = 3


def pieces_for(plan: dict[str, Any], src_w: int, src_h: int) -> list[Piece]:
    """Render pieces from a stored plan (pure): crops, plus the flash after the teaser."""
    raw = plan.get("pieces", [])
    has_teaser = any(p.get("part") == "teaser" for p in raw)
    last_teaser = max((i for i, p in enumerate(raw) if p.get("part") == "teaser"), default=-1)
    out = []
    for i, p in enumerate(raw):
        shot = Shot(
            p["start"], p["end"], p["cx"], p["cy"], p.get("zoom", 1.0), p.get("face_h", 0.0)
        )
        out.append(
            Piece(
                start=shot.start,
                end=shot.end,
                crop=crop_box(src_w, src_h, shot),
                flash_out=i == last_teaser,
                flash_in=has_teaser and i == last_teaser + 1,
            )
        )
    return out


def _size_of(plan: dict[str, Any]) -> tuple[int, int] | None:
    """The render size the edit plan chose (None for older plans: render picks one)."""
    value = plan.get("size")
    return (int(value[0]), int(value[1])) if isinstance(value, list) and len(value) == 2 else None


def _captions_for(words: list[Word], title: str | None, font: str) -> CaptionsFor:
    """Captions for one rendered piece, so each piece is encoded with its own text burned in."""

    def build(start: float, end: float) -> str:
        return build_ass(words, title=title, font=font, window=(start, end))

    return build


def run(ctx: StageContext) -> StageOutput:
    with ctx.sessions() as db:
        src = db.query(SourceVideo).filter_by(project_id=ctx.project_id).one_or_none()
        if src is None or not src.width or not src.height:
            raise PermanentStageError("no_source", "The source video is missing.")
        source_key = src.storage_key
        src_w, src_h = int(src.width), int(src.height)
        clips = db.query(Clip).filter_by(project_id=ctx.project_id).order_by(Clip.rank).all()
        rendered = {a.clip_id for c in clips for a in c.assets if a.kind == AssetKind.VIDEO}
        # Clips that failed before are retried here: "Try again" re-runs this stage, and a
        # failure is usually transient (a killed encoder, a full disk). MAX_CLIP_ATTEMPTS stops
        # a genuinely broken clip from being retried forever.
        todo = [
            (c.id, c.title, dict(c.edit_plan.get("render") or {}))
            for c in clips
            if c.id not in rendered and "render" in c.edit_plan and c.attempts < MAX_CLIP_ATTEMPTS
        ]
        already = len(rendered)
    if not todo:
        if already:
            return StageOutput({"rendered": 0, "existing": already}, skipped=True)
        raise PermanentStageError(
            "nothing_to_render",
            "We couldn't render this video's clips, even after retrying.",
        )

    source = local_source(ctx, source_key)
    done, failed = 0, 0
    for clip_id, title, plan in todo:
        with ctx.sessions() as db:
            clip = db.get(Clip, clip_id)
            if clip is not None and clip.status == ClipStatus.FAILED:
                clip.status, clip.error_message = ClipStatus.PLANNED, None
                db.commit()
        out = ctx.work_dir / f"{clip_id}.mp4"
        thumb = ctx.work_dir / f"{clip_id}.jpg"
        words = [Word(t, s, e) for t, s, e in plan.get("words", [])]
        try:
            render(
                source,
                pieces_for(plan, src_w, src_h),
                out,
                ctx.work_dir / f"render-{clip_id}",
                None,
                preset=ctx.settings.render_preset,
                crf=ctx.settings.render_crf,
                size=_size_of(plan),
                captions=_captions_for(words, title, ctx.settings.caption_font),
            )
            make_thumbnail(str(out), thumb, at_seconds=min(1.0, float(plan.get("duration", 2)) / 2))
        except MediaError as exc:
            logger.warning("clip_render_failed", extra={"clip_id": str(clip_id), "err": str(exc)})
            with ctx.sessions() as db:
                clip = db.get(Clip, clip_id)
                if clip is not None:
                    clip.status = ClipStatus.FAILED
                    clip.attempts += 1
                    clip.error_message = "This clip couldn't be rendered."
                    clip.qa_report = {"render_error": str(exc)[:1000]}
                    db.commit()
            failed += 1
            continue

        video_key = f"{ctx.prefix}clips/{clip_id}.mp4"
        thumb_key = f"{ctx.prefix}clips/{clip_id}.jpg"
        try:
            v = ctx.storage.upload_file(out, video_key, "video/mp4")
            t = ctx.storage.upload_file(thumb, thumb_key, "image/jpeg")
        except OSError as exc:
            raise RetryableStageError("storage_error", "Saving a rendered clip failed.") from exc
        # Check it straight away so the clip can be watched and downloaded while the rest of
        # the video is still rendering, instead of everyone waiting for the whole batch.
        problems = verify(ctx, video_key, float(plan.get("duration", 0)), _size_of(plan))
        with ctx.sessions() as db:
            clip = db.get(Clip, clip_id)
            if clip is None:
                continue
            db.add(
                ClipAsset(
                    clip_id=clip_id,
                    kind=AssetKind.VIDEO,
                    storage_key=video_key,
                    size_bytes=v.size_bytes,
                )
            )
            db.add(
                ClipAsset(
                    clip_id=clip_id,
                    kind=AssetKind.THUMBNAIL,
                    storage_key=thumb_key,
                    size_bytes=t.size_bytes,
                )
            )
            clip.attempts += 1
            clip.qa_report = problems.report
            if problems.problems:
                clip.status = ClipStatus.FAILED
                clip.error_message = "This clip failed the quality check."
            else:
                clip.status = ClipStatus.READY
                clip.duration_seconds = round(problems.duration, 2)
                for asset in clip.assets:
                    asset.is_final = True
            db.commit()
        out.unlink(missing_ok=True)
        done += 1
        ctx.heartbeat()

    if done == 0 and already == 0:
        raise PermanentStageError("render_failed", "We couldn't render any clips from this video.")
    return StageOutput({"rendered": done, "failed": failed})
