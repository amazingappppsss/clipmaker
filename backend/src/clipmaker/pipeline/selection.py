"""Clip selection rules (PRD §5.4) — pure functions, no I/O, fully unit-tested.

The LLM proposes candidate moments as *segment ranges* and scores them per editorial signal.
This module turns proposals into final clips:
1. validate/normalise the range so the clip spans whole sentences within duration limits
2. compute the weighted score (configurable weights; initial heuristics, not proven science)
3. drop near-duplicates (keep the stronger)
4. keep the best N above the quality bar — fewer great clips beat padding with weak ones
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from clipmaker.pipeline.transcript import Segment

SIGNALS = (
    "standalone_context",
    "strong_opening",
    "story_payoff",
    "emotional_engagement",
    "information_value",
    "natural_ending",
)
LEAD_IN_SECONDS = 0.15  # breathing room before the first word
TAIL_SECONDS = 0.35  # let the last word finish
MAX_OVERLAP_FRACTION = 0.35  # of the shorter clip


@dataclass(slots=True)
class Proposal:
    """A candidate as proposed by the model."""

    start_segment: int
    end_segment: int
    category: str
    rationale: str
    hook_line: str
    scores: dict[str, float]


@dataclass(slots=True)
class ScoredCandidate:
    """A proposal after normalisation and scoring."""

    proposal: Proposal
    start_segment: int
    end_segment: int
    start_seconds: float
    end_seconds: float
    total_score: float
    adjusted: bool = False
    rejected_reason: str | None = None
    selected: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds


def parse_weights(raw: str) -> dict[str, float]:
    """Parse and normalise weights so they sum to 1. Unknown keys are rejected."""
    data: dict[str, Any] = json.loads(raw)
    unknown = set(data) - set(SIGNALS)
    if unknown:
        raise ValueError(f"Unknown score signals: {sorted(unknown)}")
    weights = {k: float(data.get(k, 0.0)) for k in SIGNALS}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Score weights must sum to a positive number")
    return {k: v / total for k, v in weights.items()}


def weighted_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    """0-100 score from per-signal 0-10 ratings (missing signals count as 0)."""
    total = sum(weights[s] * min(max(float(scores.get(s, 0.0)), 0.0), 10.0) for s in SIGNALS)
    return round(total * 10.0, 2)


def auto_clip_count(duration_seconds: float) -> int:
    """Default number of clips when the user picks "Auto"."""
    minutes = duration_seconds / 60
    if minutes < 10:
        return 3
    if minutes < 30:
        return 5
    if minutes < 75:
        return 8
    return 10


def _span(segments: list[Segment], start: int, end: int) -> float:
    return segments[end].end - segments[start].start


def normalise_range(
    segments: list[Segment], start: int, end: int, min_s: float, max_s: float
) -> tuple[int, int, bool, str | None]:
    """Make [start, end] a valid whole-sentence range within duration limits.

    Too long  → drop trailing sentences (then leading ones) until it fits.
    Too short → extend with the following sentences (then preceding ones).
    Returns (start, end, adjusted, rejected_reason).
    """
    n = len(segments)
    if n == 0:
        return start, end, False, "empty transcript"
    if start > end:
        start, end = end, start
    if start < 0 or end >= n:
        return start, end, False, "segment range out of bounds"
    adjusted = False
    while _span(segments, start, end) > max_s and end > start:
        end -= 1
        adjusted = True
    while _span(segments, start, end) > max_s and start < end:
        start += 1
        adjusted = True
    if _span(segments, start, end) > max_s:
        return start, end, adjusted, "a single sentence exceeds the maximum clip length"
    while _span(segments, start, end) < min_s and end + 1 < n:
        if _span(segments, start, end + 1) > max_s:
            break
        end += 1
        adjusted = True
    while _span(segments, start, end) < min_s and start > 0:
        if _span(segments, start - 1, end) > max_s:
            break
        start -= 1
        adjusted = True
    if _span(segments, start, end) < min_s:
        return start, end, adjusted, "too short to stand alone"
    return start, end, adjusted, None


def clip_times(segments: list[Segment], start: int, end: int) -> tuple[float, float]:
    """Cut points with a little breathing room, never bleeding into neighbouring speech."""
    begin = segments[start].start - LEAD_IN_SECONDS
    if start > 0:
        begin = max(begin, segments[start - 1].end)
    finish = segments[end].end + TAIL_SECONDS
    if end + 1 < len(segments):
        finish = min(finish, segments[end + 1].start)
    return round(max(begin, 0.0), 3), round(finish, 3)


def overlap_fraction(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Overlap as a fraction of the shorter interval."""
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    shorter = min(a[1] - a[0], b[1] - b[0])
    return inter / shorter if shorter > 0 else 0.0


def select_clips(
    proposals: list[Proposal],
    segments: list[Segment],
    weights: dict[str, float],
    target_count: int,
    min_s: float,
    max_s: float,
    min_score: float,
) -> list[ScoredCandidate]:
    """Score, validate, dedupe and pick. Returns *all* candidates (selected flag set) so
    decisions are auditable in the `candidates` table."""
    scored: list[ScoredCandidate] = []
    for p in proposals:
        s, e, adjusted, reason = normalise_range(
            segments, p.start_segment, p.end_segment, min_s, max_s
        )
        if reason is None:
            t0, t1 = clip_times(segments, s, e)
        else:
            t0 = t1 = 0.0
        scored.append(
            ScoredCandidate(
                proposal=p,
                start_segment=s,
                end_segment=e,
                start_seconds=t0,
                end_seconds=t1,
                total_score=weighted_score(p.scores, weights),
                adjusted=adjusted,
                rejected_reason=reason,
            )
        )

    chosen: list[ScoredCandidate] = []
    for cand in sorted(scored, key=lambda c: c.total_score, reverse=True):
        if cand.rejected_reason:
            continue
        if any(
            overlap_fraction(
                (cand.start_seconds, cand.end_seconds), (c.start_seconds, c.end_seconds)
            )
            > MAX_OVERLAP_FRACTION
            for c in chosen
        ):
            cand.rejected_reason = "overlaps a stronger moment"
            continue
        if len(chosen) >= target_count:
            cand.rejected_reason = "not in the top picks"
            continue
        if cand.total_score < min_score and chosen:
            cand.rejected_reason = "below the quality bar"
            continue
        if cand.total_score < min_score:
            cand.notes.append("best available moment is below the quality bar")
        cand.selected = True
        chosen.append(cand)
    return scored
