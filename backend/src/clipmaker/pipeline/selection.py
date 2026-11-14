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

# STOP · STAY · SHARE signals (docs/CLIP_FRAMEWORK.md), each rated 0-10 by the model.
SIGNALS = (
    "hook",
    "curiosity_gap",
    "stakes",
    "specificity",
    "momentum",
    "emotion",
    "transformation",
    "causality",
    "payoff",
    "share_trigger",
    "standalone",
)

# Plain-English labels for the strengths shown to creators ("why it works").
SIGNAL_LABELS = {
    "hook": "Scroll-stopping hook",
    "curiosity_gap": "Curiosity gap",
    "stakes": "Real stakes",
    "specificity": "Concrete details",
    "momentum": "No dead air",
    "emotion": "Emotional peak",
    "transformation": "Someone changes",
    "causality": "But… therefore…",
    "payoff": "Strong payoff",
    "share_trigger": "Made to share",
    "standalone": "Stands alone",
}


def strengths(scores: dict[str, float], limit: int = 3, minimum: float = 7.0) -> list[str]:
    """The clip's best signals (rated >= minimum), strongest first, as creator-facing labels."""
    ranked = sorted(
        (s for s in SIGNALS if float(scores.get(s, 0.0)) >= minimum),
        key=lambda s: float(scores.get(s, 0.0)),
        reverse=True,
    )
    return [SIGNAL_LABELS[s] for s in ranked[:limit]]


# Hard gates: a clip that fails one of these never ships, however well it scores elsewhere.
GATES: dict[str, tuple[float, str]] = {
    "standalone": (4.0, "needs outside context to make sense"),
    "payoff": (4.0, "ends without a payoff"),
    "hook": (3.0, "opening won't stop the scroll"),
}
# When fewer clips clear the quality bar, still show up to this many if they're close to it.
MIN_SHOWN = 3
NEAR_BAR_MARGIN = 15.0
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
    # Story anatomy (Storyworthy): five_second_moment, before_state, after_state,
    # missing_context — empty strings when the clip isn't a story.
    story: dict[str, str] = field(default_factory=dict)
    # Flash-forward hook proposed by the model (segment index inside the clip, or -1).
    teaser_segment: int = -1
    teaser_reason: str = ""
    hook_type: str = "none"


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


LENGTH_PENALTY_PER_SECOND = 0.6  # points lost per second beyond the ideal maximum


def length_penalty(duration: float, ideal_max: float) -> float:
    """Points subtracted for running long (0 within the ideal length, ~15 at 60 s)."""
    return round(max(0.0, duration - ideal_max) * LENGTH_PENALTY_PER_SECOND, 2)


def weighted_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    """0-100 score from per-signal 0-10 ratings (missing signals count as 0)."""
    total = sum(weights[s] * min(max(float(scores.get(s, 0.0)), 0.0), 10.0) for s in SIGNALS)
    return round(total * 10.0, 2)


def auto_clip_count(duration_seconds: float) -> int:
    """Upper bound on clips for "Auto": about one per 90 s of video, between 3 and 12.

    It is a ceiling, not a quota — only moments that clear the quality bar are shown.
    """
    return int(min(12, max(3, round(duration_seconds / 90))))


def gate_failure(scores: dict[str, float]) -> str | None:
    """The first hard gate a clip fails, or None."""
    for signal, (minimum, reason) in GATES.items():
        if float(scores.get(signal, 0.0)) < minimum:
            return reason
    return None


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
    ideal_max: float | None = None,
) -> list[ScoredCandidate]:
    """Score, validate, dedupe and pick. Returns *all* candidates (selected flag set) so
    decisions are auditable in the `candidates` table."""
    scored: list[ScoredCandidate] = []
    for p in proposals:
        s, e, adjusted, reason = normalise_range(
            segments, p.start_segment, p.end_segment, min_s, max_s
        )
        if reason is None:
            reason = gate_failure(p.scores)
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
                total_score=max(
                    0.0,
                    weighted_score(p.scores, weights)
                    - (length_penalty(t1 - t0, ideal_max) if ideal_max else 0.0),
                ),
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
        if cand.total_score < min_score:
            near = cand.total_score >= min_score - NEAR_BAR_MARGIN
            if chosen and not (near and len(chosen) < MIN_SHOWN):
                cand.rejected_reason = "below the quality bar"
                continue
            cand.notes.append("below the quality bar; shown as one of the best available")
        cand.selected = True
        chosen.append(cand)
    return scored


TEASER_MIN_SECONDS = 1.5
TEASER_MAX_SECONDS = 6.0


def pick_teaser(
    segments: list[Segment], start: int, end: int, proposed: int
) -> tuple[int, float, float] | None:
    """Validate the model's flash-forward line for a clip spanning segments [start, end].

    It must sit strictly inside the clip (the first line already plays first; the last line is
    the payoff, which a teaser must not spoil) and be short enough to work as a 2-6 s hook.
    Returns (segment, start_seconds, end_seconds) or None when no teaser should be used.
    """
    if not start < proposed < end:
        return None
    seg = segments[proposed]
    length = seg.end - seg.start
    if not TEASER_MIN_SECONDS <= length <= TEASER_MAX_SECONDS:
        return None
    return proposed, round(seg.start, 3), round(seg.end, 3)
