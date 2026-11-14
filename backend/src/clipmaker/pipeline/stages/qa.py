"""QUALITY_CHECK: verify every rendered file before anyone can download it.

A clip is published (asset `is_final`) only if the file is a real 1080x1920 video with audio
and the expected length. Anything else is marked failed with the reason — never shown broken.
"""

from __future__ import annotations

from typing import Any

from clipmaker.core.enums import AssetKind, ClipStatus
from clipmaker.db.models import Clip, SourceVideo
from clipmaker.editing.render import OUT_H, OUT_W
from clipmaker.media.probe import ProbeError, probe_media
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError

DURATION_TOLERANCE = 0.75  # seconds


def check(meta: Any, expected: float) -> list[str]:
    """Problems with a rendered file (pure). Empty list = passed."""
    problems = []
    if (meta.width, meta.height) != (OUT_W, OUT_H):
        problems.append(f"resolution {meta.width}x{meta.height}, expected {OUT_W}x{OUT_H}")
    if not meta.has_audio:
        problems.append("no audio track")
    if expected and abs(meta.duration_seconds - expected) > DURATION_TOLERANCE:
        problems.append(f"length {meta.duration_seconds:.1f}s, expected {expected:.1f}s")
    if meta.duration_seconds < 3:
        problems.append("too short")
    return problems


def run(ctx: StageContext) -> StageOutput:
    with ctx.sessions() as db:
        clips = db.query(Clip).filter_by(project_id=ctx.project_id).all()
        todo = []
        for c in clips:
            if c.status != ClipStatus.QA:
                continue
            video = next((a for a in c.assets if a.kind == AssetKind.VIDEO), None)
            if video is not None:
                todo.append((c.id, video.storage_key, float(c.duration_seconds or 0)))
        ready_before = sum(1 for c in clips if c.status == ClipStatus.READY)

    passed = 0
    for clip_id, key, expected in todo:
        try:
            meta = probe_media(ctx.storage.media_source(key))
            problems = check(meta, expected)
            report: dict[str, Any] = {
                "width": meta.width,
                "height": meta.height,
                "duration": meta.duration_seconds,
                "has_audio": meta.has_audio,
                "problems": problems,
            }
        except ProbeError as exc:
            problems, report = ["unreadable file"], {"problems": [str(exc)]}
        with ctx.sessions() as db:
            clip = db.get(Clip, clip_id)
            if clip is None:
                continue
            clip.qa_report = report
            if problems:
                clip.status = ClipStatus.FAILED
                clip.error_message = "This clip failed the quality check."
            else:
                clip.status = ClipStatus.READY
                clip.duration_seconds = round(float(report["duration"]), 2)
                for a in clip.assets:
                    a.is_final = True
                passed += 1
            db.commit()

    if passed + ready_before == 0:
        raise PermanentStageError("qa_failed", "None of the rendered clips passed quality checks.")
    freed = _free_source_files(ctx)
    return StageOutput({"passed": passed, "checked": len(todo), "freed": freed}, skipped=not todo)


def _free_source_files(ctx: StageContext) -> int:
    """Once finished clips exist, the long source video and its audio aren't needed any more.

    Deleting them keeps storage small (a podcast is hundreds of MB; its clips a few dozen).
    Transcript, clips and the project thumbnail are kept. Returns files removed.
    """
    with ctx.sessions() as db:
        src = db.query(SourceVideo).filter_by(project_id=ctx.project_id).one_or_none()
        keys = [src.storage_key] if src is not None else []
    keys.append(f"{ctx.prefix}work/audio.mp3")
    return sum(ctx.storage.delete_prefix(k) for k in keys)
