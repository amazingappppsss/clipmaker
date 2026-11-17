"""SELECTING: candidate generation (smart model) → scoring/dedupe (code) → metadata (fast model).

Writes every candidate (with its scores and why it was or wasn't chosen) to `candidates`, and the
chosen ones to `clips` (status PLANNED) with titles, hooks, captions and hashtags.
Idempotent: if clips already exist for the project, nothing is regenerated.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import partial
from typing import Any

from clipmaker.core.enums import ClipStatus, VideoStyle
from clipmaker.db.models import Candidate, Clip, Project, SourceVideo, VideoAnalysis
from clipmaker.editing.energy import loud_moments
from clipmaker.media.probe import ProbeError, probe_media
from clipmaker.pipeline.action import ActionRange, action_ranges
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError
from clipmaker.pipeline.prompts import (
    ACTION_INSTRUCTION,
    ACTION_SCHEMA,
    CANDIDATES_INSTRUCTION,
    CANDIDATES_SCHEMA,
    METADATA_INSTRUCTION,
    METADATA_SCHEMA,
    SYSTEM_EDITOR,
)
from clipmaker.pipeline.selection import (
    ACTION,
    Proposal,
    ScoredCandidate,
    auto_clip_count,
    gate_failure,
    parse_weights,
    pick_teaser,
    select_clips,
)
from clipmaker.pipeline.stages.common import (
    load_segments,
    parallel_parts,
    run_parallel,
    split_for_parallel,
)
from clipmaker.pipeline.transcript import Segment, render_for_llm
from clipmaker.providers.llm.base import LLMError, LLMRequest

MAX_PROPOSALS_PER_CALL = 20


def _llm_call(ctx: StageContext, request: LLMRequest, code: str) -> tuple[dict[str, Any], Decimal]:
    try:
        result = ctx.llm().complete_json(request)
    except LLMError as exc:
        error = RetryableStageError if exc.retryable else PermanentStageError
        raise error(code, str(exc)) from exc
    ctx.heartbeat()
    return result.data, result.cost_usd


def _int_or(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


STORY_FIELDS = ("five_second_moment", "before_state", "after_state", "missing_context")


def parse_proposals(data: dict[str, Any], segment_count: int) -> list[Proposal]:
    """Validate model output defensively (pure). Bad entries are skipped, not trusted."""
    proposals = []
    for c in data.get("candidates", []):
        try:
            start, end = int(c["start_segment"]), int(c["end_segment"])
            scores = {k: float(v) for k, v in dict(c["scores"]).items()}
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= start < segment_count and 0 <= end < segment_count):
            continue
        proposals.append(
            Proposal(
                start_segment=start,
                end_segment=end,
                category=str(c.get("category", "other")),
                rationale=str(c.get("rationale", "")),
                hook_line=str(c.get("hook_line", "")),
                scores=scores,
                story={k: str(c.get(k) or "")[:500] for k in STORY_FIELDS},
                teaser_segment=_int_or(c.get("teaser_segment"), -1),
                teaser_reason=str(c.get("teaser_reason") or "")[:300],
                hook_type=str(c.get("hook_type") or "none")[:30],
            )
        )
    return proposals


def _teaser_plan(segments: list[Segment], c: ScoredCandidate) -> dict[str, Any] | None:
    """Flash-forward hook for the edit plan, or None (validated by selection.pick_teaser)."""
    picked = pick_teaser(segments, c.start_segment, c.end_segment, c.proposal.teaser_segment)
    if picked is None:
        return None
    idx, t0, t1 = picked
    return {
        "segment": idx,
        "start": t0,
        "end": t1,
        "text": segments[idx].text,
        "reason": c.proposal.teaser_reason,
    }


def _clip_text(segments: list[Segment], c: ScoredCandidate) -> str:
    return " ".join(s.text for s in segments[c.start_segment : c.end_segment + 1])


def energy_source(ctx: StageContext) -> str | None:
    """Something FFmpeg can measure the loudness of, cheapest first, or None.

    The extracted audio track is a fraction of the video to read, and transcription already
    produced it for most projects.
    """
    local = ctx.work_dir / "audio.mp3"
    if local.is_file():
        return str(local)
    audio_key = f"{ctx.prefix}work/audio.mp3"
    if ctx.storage.head(audio_key):
        return ctx.storage.media_source(audio_key)
    with ctx.sessions() as db:
        src = db.query(SourceVideo).filter_by(project_id=ctx.project_id).one_or_none()
        key = src.storage_key if src else None
    return ctx.storage.media_source(key) if key else None


def parse_action_scores(data: dict[str, Any], count: int) -> dict[int, dict[str, Any]]:
    """Model output keyed by the index we gave it (pure). Bad entries are skipped."""
    out: dict[int, dict[str, Any]] = {}
    for row in data.get("moments", []):
        if not isinstance(row, dict):
            continue
        try:
            index = int(row["index"])
            scores = {k: float(v) for k, v in dict(row["scores"]).items()}
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= index < count:
            out[index] = {
                "scores": scores,
                "title": str(row.get("title") or "")[:200],
                "what_happens": str(row.get("what_happens") or "")[:500],
            }
    return out


def describe_moments(ranges: list[ActionRange]) -> str:
    """The moments as the model sees them (pure)."""
    return "\n\n".join(
        f"[{i}] +{r.above_median_db:.0f} dB over the baseline. "
        f"Said over it: {r.text.strip() or '(nothing)'}"
        for i, r in enumerate(ranges)
    )


def action_proposals(
    ctx: StageContext,
    segments: list[Segment],
    proposed: list[tuple[float, float]],
) -> tuple[list[Proposal], Decimal]:
    """Candidates found by sound rather than by words, scored by the fast model.

    Returns ([], 0) whenever there is nothing to add — no audio, no spikes, every spike
    already proposed, or the scoring call failing. Gameplay is a bonus source here, never a
    reason for the stage to fail.
    """
    source = energy_source(ctx)
    if source is None:
        return [], Decimal(0)
    # The media's own length, not the transcript's: loudness windows are timed against it, and
    # a transcript ends where the talking stops, which is not where the file does.
    try:
        duration = probe_media(source).duration_seconds
    except ProbeError:
        return [], Decimal(0)
    if duration <= 0:
        return [], Decimal(0)
    moments = loud_moments(source, duration)
    ctx.heartbeat()
    ranges = action_ranges(
        moments, segments, proposed, ctx.settings.min_clip_seconds, ctx.settings.max_clip_seconds
    )
    if not ranges:
        return [], Decimal(0)
    try:
        data, cost = _llm_call(
            ctx,
            LLMRequest(
                tier="fast",
                system=SYSTEM_EDITOR,
                context=render_for_llm(segments),
                instruction=ACTION_INSTRUCTION.format(moments=describe_moments(ranges)),
                schema=ACTION_SCHEMA,
            ),
            "action_scoring_failed",
        )
    except (RetryableStageError, PermanentStageError):
        return [], Decimal(0)
    scored = parse_action_scores(data, len(ranges))
    out = []
    for i, r in enumerate(ranges):
        judged = scored.get(i)
        if judged is None:
            continue
        out.append(
            Proposal(
                start_segment=r.start_segment,
                end_segment=r.end_segment,
                category="funny",
                rationale=str(judged["what_happens"]),
                hook_line=str(judged["title"]),
                scores=dict(judged["scores"]),
                kind=ACTION,
            )
        )
    return out, cost


def run(ctx: StageContext) -> StageOutput:
    with ctx.sessions() as db:
        if db.query(Clip).filter_by(project_id=ctx.project_id).count() > 0:
            return StageOutput({"clips": "existing"}, skipped=True)
        project = db.get(Project, ctx.project_id)
        analysis_row = db.query(VideoAnalysis).filter_by(project_id=ctx.project_id).one_or_none()
        if project is None or analysis_row is None:
            raise PermanentStageError("no_analysis", "Video analysis missing; it must run first.")
        settings: dict[str, Any] = dict(project.settings)
        analysis: dict[str, Any] = dict(analysis_row.analysis)

    segments = load_segments(ctx)
    duration = segments[-1].end if segments else 0.0
    requested = settings.get("clip_count", "auto")
    target = auto_clip_count(duration) if requested == "auto" else int(requested)
    style = settings.get("style", "auto")
    style = VideoStyle.MODERN_CREATOR.value if style in (None, "auto") else str(style)
    s = ctx.settings
    analysis_json = json.dumps(analysis, sort_keys=True, ensure_ascii=False)

    # 1) Candidate proposals from the smart model, per window (same cached transcript prefix).
    lengths = [len(render_for_llm([seg])) + 1 for seg in segments]
    parts = parallel_parts(ctx.settings)
    spans = split_for_parallel(segments, lengths, parts)
    per_part = min(MAX_PROPOSALS_PER_CALL, max(3, (target * 2 + 2) // len(spans) + 1))

    def hunt(span: tuple[int, int]) -> tuple[dict[str, Any], Decimal]:
        start, end = span
        return _llm_call(
            ctx,
            LLMRequest(
                tier="smart",
                system=SYSTEM_EDITOR,
                context=render_for_llm(segments[start : end + 1]),
                instruction=CANDIDATES_INSTRUCTION.format(
                    analysis=analysis_json,
                    count=per_part,
                    min_s=s.min_clip_seconds,
                    max_s=s.max_clip_seconds,
                ),
                schema=CANDIDATES_SCHEMA,
            ),
            "selection_failed",
        )

    # The parts are hunted at the same time: one call over a whole transcript was by far the
    # slowest step in the pipeline, and each part is judged with the same whole-video analysis.
    proposals: list[Proposal] = []
    cost = Decimal(0)
    for data, c in run_parallel([partial(hunt, span) for span in spans], workers=parts):
        proposals.extend(parse_proposals(data, len(segments)))
        cost += c
    if not proposals:
        raise RetryableStageError("no_candidates", "The model proposed no usable moments.")

    # 1b) Moments found by sound. Every signal above reads a transcript, so a crash, a clutch
    # or a jumpscare is invisible to the hunter however clippable it is.
    action_count = 0
    if s.enable_action_moments:
        # Only moments the hunter proposed *and* would ship: a loud moment sitting under a
        # proposal that fails its own gates has had no chance yet, and judged as action it
        # may well pass.
        proposed_spans = [
            (segments[p.start_segment].start, segments[p.end_segment].end)
            for p in proposals
            if 0 <= p.start_segment < len(segments)
            and 0 <= p.end_segment < len(segments)
            and gate_failure(p.scores, p.kind) is None
        ]
        found, action_cost = action_proposals(ctx, segments, proposed_spans)
        proposals.extend(found)
        cost += action_cost
        action_count = len(found)

    # 2) Deterministic scoring, validation, dedupe and top-N.
    scored = select_clips(
        proposals,
        segments,
        parse_weights(s.score_weights_json),
        target,
        s.min_clip_seconds,
        s.max_clip_seconds,
        s.min_clip_score,
        ideal_max=s.ideal_max_clip_seconds,
    )
    chosen = sorted((c for c in scored if c.selected), key=lambda c: c.total_score, reverse=True)
    if not chosen:
        raise PermanentStageError(
            "no_valid_moments", "We couldn't find a moment that works as a standalone clip."
        )

    # 3) Publishing metadata from the fast model (grounded in each clip's own words).
    clip_listing = "\n\n".join(
        f"Clip {i + 1} ({c.duration:.0f}s): {_clip_text(segments, c)}" for i, c in enumerate(chosen)
    )
    meta, c = _llm_call(
        ctx,
        LLMRequest(
            tier="fast",
            system=SYSTEM_EDITOR,
            context=clip_listing,
            instruction=METADATA_INSTRUCTION.format(clips="(see the clips above)"),
            schema=METADATA_SCHEMA,
            max_tokens=8000,
        ),
        "metadata_failed",
    )
    cost += c
    by_number = {
        int(m.get("clip_number", 0)): m for m in meta.get("clips", []) if isinstance(m, dict)
    }

    with ctx.sessions() as db:
        rank = 0
        for cand in scored:
            row = Candidate(
                project_id=ctx.project_id,
                start_seconds=cand.start_seconds,
                end_seconds=cand.end_seconds,
                category=cand.proposal.category,
                rationale=cand.proposal.rationale,
                scores={
                    **cand.proposal.scores,
                    "start_segment": cand.start_segment,
                    "end_segment": cand.end_segment,
                    "adjusted": cand.adjusted,
                    "story": cand.proposal.story,
                    "hook_type": cand.proposal.hook_type,
                    "kind": cand.proposal.kind,
                },
                total_score=cand.total_score,
                plan={
                    "start": cand.start_seconds,
                    "end": cand.end_seconds,
                    "start_segment": cand.start_segment,
                    "end_segment": cand.end_segment,
                    "transcript": _clip_text(segments, cand),
                    "hook_line": cand.proposal.hook_line,
                    "notes": cand.notes,
                    "teaser": _teaser_plan(segments, cand),
                },
                selected=cand.selected,
                rejected_reason=cand.rejected_reason,
            )
            db.add(row)
            db.flush()
            if not cand.selected:
                continue
            rank += 1
            m = by_number.get(chosen.index(cand) + 1, {})
            db.add(
                Clip(
                    project_id=ctx.project_id,
                    candidate_id=row.id,
                    rank=rank,
                    status=ClipStatus.PLANNED,
                    title=str(m.get("title") or cand.proposal.hook_line)[:200],
                    hook=str(m.get("hook") or cand.proposal.hook_line)[:300],
                    alt_titles=[str(t) for t in m.get("alt_titles", [])][:3],
                    social_caption=str(m.get("social_caption", "")) or None,
                    hashtags=[str(h) for h in m.get("hashtags", [])][:6],
                    style=style,
                    duration_seconds=round(cand.duration, 2),
                    edit_plan={
                        "start": cand.start_seconds,
                        "end": cand.end_seconds,
                        "start_segment": cand.start_segment,
                        "end_segment": cand.end_segment,
                        "transcript": _clip_text(segments, cand),
                        "notes": cand.notes,
                        "teaser": _teaser_plan(segments, cand),
                    },
                )
            )
        db.commit()
    return StageOutput(
        {
            "candidates": len(scored),
            "selected": len(chosen),
            "target": target,
            "action_candidates": action_count,
        },
        cost_usd=cost,
    )
