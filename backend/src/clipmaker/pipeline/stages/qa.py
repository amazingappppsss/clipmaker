"""QUALITY_CHECK: verify every rendered file before anyone can download it.

A clip is published (asset `is_final`) only if the file is a real vertical video with audio
and the expected length, and only if it actually shows and plays something. Anything else is
marked failed with the reason — never shown broken.

That last part is not theoretical: a misplaced `fade` once whited out every frame of a clip,
and the file was a perfectly valid 1080x1920 H.264 video of the right length with an audio
track. Every check here passed it. So the picture and the sound are now sampled, not just
described.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from clipmaker.core.enums import AssetKind, ClipStatus
from clipmaker.db.models import Clip, SourceVideo
from clipmaker.editing.render import SIZES
from clipmaker.editing.report import report, summarise
from clipmaker.media.probe import (
    BLANK_STDDEV,
    SILENT_DBFS,
    ProbeError,
    frame_variation,
    mean_volume_dbfs,
    probe_media,
)
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError

# Every kept stretch is snapped to whole frames, so a finished clip drifts a little from the
# planned length. This check is here to catch a broken file, not a third of a second.
DURATION_TOLERANCE = 1.5  # seconds
DURATION_TOLERANCE_FRACTION = 0.08


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the quality check found for one rendered file."""

    problems: list[str]
    report: dict[str, Any]
    duration: float


def verify(
    ctx: StageContext, storage_key: str, expected: float, size: tuple[int, int] | None = None
) -> Verdict:
    """Probe a rendered clip in storage and judge it (used per clip and as a final sweep)."""
    try:
        meta = probe_media(ctx.storage.media_source(storage_key))
    except ProbeError as exc:
        return Verdict(["unreadable file"], {"problems": [str(exc)]}, 0.0)
    source = ctx.storage.media_source(storage_key)
    # Three frames spread across the clip: a blank opening is as bad as a blank middle, and
    # sampling is cheap next to the render that produced the file.
    length = meta.duration_seconds or expected or 0.0
    variations = [frame_variation(source, at) for at in (length * 0.1, length * 0.5, length * 0.9)]
    volume = mean_volume_dbfs(source) if meta.has_audio else None

    problems = check(meta, expected, size, variations, volume)
    return Verdict(
        problems,
        {
            "width": meta.width,
            "height": meta.height,
            "duration": meta.duration_seconds,
            "has_audio": meta.has_audio,
            "frame_variation": [round(v, 2) if v is not None else None for v in variations],
            "mean_volume_dbfs": round(volume, 1) if volume is not None else None,
            "problems": problems,
        },
        meta.duration_seconds,
    )


def looks_blank(variations: list[float | None]) -> bool:
    """Whether every frame we could measure was a flat colour (pure).

    Measured frames only: if none could be measured we say nothing rather than failing a clip
    over a missing tool.
    """
    measured = [v for v in variations if v is not None]
    return bool(measured) and all(v < BLANK_STDDEV for v in measured)


def check(
    meta: Any,
    expected: float,
    size: tuple[int, int] | None = None,
    variations: list[float | None] | None = None,
    volume_dbfs: float | None = None,
) -> list[str]:
    """Problems with a rendered file (pure). Empty list = passed."""
    problems = []
    if size is not None and (meta.width, meta.height) != size:
        problems.append(f"resolution {meta.width}x{meta.height}, expected {size[0]}x{size[1]}")
    elif size is None and (meta.width, meta.height) not in SIZES:
        problems.append(f"resolution {meta.width}x{meta.height} is not a supported vertical size")
    if not meta.has_audio:
        problems.append("no audio track")
    allowed = max(DURATION_TOLERANCE, expected * DURATION_TOLERANCE_FRACTION)
    if expected and abs(meta.duration_seconds - expected) > allowed:
        problems.append(f"length {meta.duration_seconds:.1f}s, expected {expected:.1f}s")
    if meta.duration_seconds < 3:
        problems.append("too short")
    if variations is not None and looks_blank(variations):
        problems.append("every sampled frame is a flat colour — the picture is blank")
    if volume_dbfs is not None and volume_dbfs <= SILENT_DBFS:
        problems.append(f"audio is silent ({volume_dbfs:.0f} dBFS)")
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
        verdict = verify(ctx, key, expected)
        problems, verdict_report = verdict.problems, verdict.report
        with ctx.sessions() as db:
            clip = db.get(Clip, clip_id)
            if clip is None:
                continue
            # The file is sound; now measure the edit itself against the framework. This is
            # feedback, not a gate: a clip that drags is still a clip, and the viewer can see
            # what we think is wrong with it and trim it themselves.
            card = summarise(report(dict(clip.edit_plan.get("render") or {})))
            clip.qa_report = {**verdict_report, "card": card}
            if problems:
                clip.status = ClipStatus.FAILED
                clip.error_message = "This clip failed the quality check."
            else:
                clip.status = ClipStatus.READY
                clip.duration_seconds = round(float(verdict_report["duration"]), 2)
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
