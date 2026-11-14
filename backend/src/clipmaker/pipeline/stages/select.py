"""SELECTING: candidate generation (smart model) → scoring/dedupe (code) → metadata (fast model).

Writes every candidate (with its scores and why it was or wasn't chosen) to `candidates`, and the
chosen ones to `clips` (status PLANNED) with titles, hooks, captions and hashtags.
Idempotent: if clips already exist for the project, nothing is regenerated.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from clipmaker.core.enums import ClipStatus, VideoStyle
from clipmaker.db.models import Candidate, Clip, Project, VideoAnalysis
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError
from clipmaker.pipeline.prompts import (
    CANDIDATES_INSTRUCTION,
    CANDIDATES_SCHEMA,
    METADATA_INSTRUCTION,
    METADATA_SCHEMA,
    SYSTEM_EDITOR,
)
from clipmaker.pipeline.selection import (
    Proposal,
    ScoredCandidate,
    auto_clip_count,
    parse_weights,
    pick_teaser,
    select_clips,
)
from clipmaker.pipeline.stages.common import load_segments, windows
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
    spans = windows(segments, lengths)
    per_window = min(MAX_PROPOSALS_PER_CALL, max(4, (target * 2 + 2) // len(spans) + 1))
    proposals: list[Proposal] = []
    cost = Decimal(0)
    for start, end in spans:
        data, c = _llm_call(
            ctx,
            LLMRequest(
                tier="smart",
                system=SYSTEM_EDITOR,
                context=render_for_llm(segments[start : end + 1]),
                instruction=CANDIDATES_INSTRUCTION.format(
                    analysis=analysis_json,
                    count=per_window,
                    min_s=s.min_clip_seconds,
                    max_s=s.max_clip_seconds,
                ),
                schema=CANDIDATES_SCHEMA,
            ),
            "selection_failed",
        )
        proposals.extend(parse_proposals(data, len(segments)))
        cost += c
    if not proposals:
        raise RetryableStageError("no_candidates", "The model proposed no usable moments.")

    # 2) Deterministic scoring, validation, dedupe and top-N.
    scored = select_clips(
        proposals,
        segments,
        parse_weights(s.score_weights_json),
        target,
        s.min_clip_seconds,
        s.max_clip_seconds,
        s.min_clip_score,
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
                },
                total_score=cand.total_score,
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
        {"candidates": len(scored), "selected": len(chosen), "target": target}, cost_usd=cost
    )
