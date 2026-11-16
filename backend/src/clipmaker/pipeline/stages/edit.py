"""EDITING: turn each picked moment into an edit plan — smart cuts, the flash-forward teaser,
speaker-following 9:16 framing with punch-ins, and caption words on the final timeline.

Idempotent: clips that already have a render plan are skipped.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from clipmaker.core.enums import ClipStatus
from clipmaker.db.models import Candidate, Clip, SourceVideo
from clipmaker.editing.cuts import Interval, keep_intervals, map_words, total_duration
from clipmaker.editing.framing import analyze_faces, plan_shots
from clipmaker.editing.render import output_size
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError
from clipmaker.pipeline.stages.common import load_segments, local_source
from clipmaker.pipeline.transcript import Segment
from clipmaker.providers.transcription.base import Word

PLAN_VERSION = 1


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def reveal_time(segments: list[Segment], start: int, end: int, moment: str | None) -> float | None:
    """Start time of the segment holding the five-second moment (pure), if we can find it."""
    if not moment:
        return None
    key = _norm(moment)[:30]
    if len(key) < 8:
        return None
    for seg in segments[start : end + 1]:
        if key in _norm(seg.text):
            return seg.start
    return None


def _words(segments: list[Segment], start: int, end: int) -> list[Word]:
    return [w for seg in segments[start : end + 1] for w in seg.words]


#: A trim can move an edge this far from where the AI put it, in seconds. Wide enough to
#: rescue a cut that lost the payoff, narrow enough that it stays the moment that was picked.
TRIM_LIMIT = 20.0
#: However it is trimmed, a clip still has to be a clip.
MIN_CLIP_SECONDS = 5.0


def apply_trim(plan: dict[str, Any], corrections: dict[str, Any] | None) -> tuple[float, float]:
    """The clip's start and end after the viewer's trim, clamped to something sane (pure).

    Nonsense is ignored rather than refused: a stored correction that no longer makes sense
    against a re-planned clip must not be able to wedge the render.
    """
    start, end = float(plan["start"]), float(plan["end"])
    if not corrections:
        return start, end

    want_start = corrections.get("start")
    want_end = corrections.get("end")
    if isinstance(want_start, int | float):
        start = min(max(float(want_start), start - TRIM_LIMIT), start + TRIM_LIMIT)
    if isinstance(want_end, int | float):
        end = min(max(float(want_end), end - TRIM_LIMIT), end + TRIM_LIMIT)

    start = max(0.0, start)
    if end - start < MIN_CLIP_SECONDS:
        end = start + MIN_CLIP_SECONDS
    return start, end


def plan_clip(
    segments: list[Segment],
    plan: dict[str, Any],
    moment: str | None,
    source: str,
    src_w: int = 1920,
    src_h: int = 1080,
    corrections: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The render plan for one clip (face analysis is the only I/O)."""
    s_seg, e_seg = int(plan["start_segment"]), int(plan["end_segment"])
    words = _words(segments, s_seg, e_seg)
    clip_start, clip_end = apply_trim(plan, corrections)
    main = keep_intervals(words, clip_start, clip_end, reveal_time(segments, s_seg, e_seg, moment))
    teaser_plan = plan.get("teaser") if isinstance(plan.get("teaser"), dict) else None
    teaser: list[Interval] = []
    teaser_words: list[Word] = []
    if teaser_plan:
        idx = int(teaser_plan["segment"])
        teaser_words = segments[idx].words
        teaser = keep_intervals(
            teaser_words, float(teaser_plan["start"]), float(teaser_plan["end"])
        )
    samples = analyze_faces(Path(source), teaser + main)
    pieces = [
        {
            "start": s.start,
            "end": s.end,
            "cx": s.cx,
            "cy": s.cy,
            "zoom": s.zoom,
            "face_h": s.face_h,
            "part": part,
        }
        for part, ivs, spoken in (("teaser", teaser, teaser_words), ("main", main, words))
        for s in plan_shots(samples, ivs, spoken)
    ]
    offset = total_duration(teaser)
    out_words = map_words(teaser_words, teaser) + map_words(words, main, offset=offset)
    out_w, out_h = output_size(src_h)
    return {
        "version": PLAN_VERSION,
        "size": [out_w, out_h],
        "pieces": pieces,
        "words": [[w.text, w.start, w.end] for w in out_words],
        "duration": round(offset + total_duration(main), 3),
        "teaser_seconds": offset,
        "faces_found": sum(1 for s in samples if s.faces),
    }


def run(ctx: StageContext) -> StageOutput:
    with ctx.sessions() as db:
        src = db.query(SourceVideo).filter_by(project_id=ctx.project_id).one_or_none()
        if src is None:
            raise PermanentStageError("no_source", "This project has no video.")
        source_key = src.storage_key
        src_w, src_h = int(src.width or 1920), int(src.height or 1080)
        todo = [
            (c.id, dict(c.edit_plan or {}), c.candidate_id, dict(c.corrections or {}))
            for c in db.query(Clip).filter_by(project_id=ctx.project_id).order_by(Clip.rank)
            if "render" not in (c.edit_plan or {})
        ]
        moments: dict[Any, str | None] = {}
        for _, _, cand_id, _ in todo:
            cand = db.get(Candidate, cand_id) if cand_id else None
            story = (cand.scores or {}).get("story") if cand else None
            moments[cand_id] = story.get("five_second_moment") if isinstance(story, dict) else None
    if not todo:
        return StageOutput({"planned": 0}, skipped=True)

    source = local_source(ctx, source_key)
    segments = load_segments(ctx)
    planned = 0
    for clip_id, plan, cand_id, corrections in todo:
        render_plan = plan_clip(
            segments, plan, moments.get(cand_id), source, src_w, src_h, corrections
        )
        with ctx.sessions() as db:
            clip = db.get(Clip, clip_id)
            if clip is None:
                continue
            clip.edit_plan = {**(clip.edit_plan or {}), "render": render_plan}
            clip.duration_seconds = render_plan["duration"]
            clip.status = ClipStatus.PLANNED
            db.commit()
        planned += 1
        ctx.heartbeat()
    return StageOutput({"planned": planned})
