"""Turning measured loud moments into clip candidates.

editing/energy.py finds where a recording got loud; selection.py judges candidates as segment
ranges. This is the bridge, and it is where gameplay stops being invisible to us: a crash or a
clutch has no quotable sentence, so the transcript-reading model never proposes it, however
obviously clippable it is.

Everything here is pure, so the rules are testable without a video or a model call.
"""

from __future__ import annotations

from dataclasses import dataclass

from clipmaker.editing.energy import Moment
from clipmaker.pipeline.transcript import Segment

#: A loud moment this close to a moment the model already proposed is the same clip; it is
#: dropped rather than offered twice under different gates.
SAME_MOMENT_SECONDS = 4.0
#: At most this many action candidates per video. They cost one scoring call between them, and
#: a long stream has hundreds of loud seconds; the loudest are the ones worth looking at.
MAX_ACTION_CANDIDATES = 8


@dataclass(frozen=True, slots=True)
class ActionRange:
    """A loud moment expressed the way selection wants it: whole segments."""

    start_segment: int
    end_segment: int
    above_median_db: float
    #: What was said over it, if anything. Often "oh my god" — sometimes nothing at all.
    text: str


def segments_covering(segments: list[Segment], start: float, end: float) -> tuple[int, int] | None:
    """The segments a stretch of seconds overlaps, or None when it overlaps none (pure)."""
    first = last = None
    for i, seg in enumerate(segments):
        if seg.end <= start or seg.start >= end:
            continue
        if first is None:
            first = i
        last = i
    if first is None or last is None:
        return None
    return first, last


def fits(segments: list[Segment], first: int, last: int, min_s: float, max_s: float) -> bool:
    """Whether this range is already a usable clip length (pure)."""
    span = segments[last].end - segments[first].start
    return min_s <= span <= max_s


def grow(
    segments: list[Segment], first: int, last: int, min_s: float, max_s: float
) -> tuple[int, int] | None:
    """Widen a range to the minimum clip length, or None when it cannot be done (pure).

    A spike can land inside a single short segment, or in a stretch of silence between two.
    Growing outwards keeps the moment in the middle, which is where the wind-up and the
    reaction both are.
    """
    if not segments:
        return None
    lo, hi = first, last
    while segments[hi].end - segments[lo].start < min_s:
        before = lo > 0
        after = hi < len(segments) - 1
        if not before and not after:
            break
        # Prefer growing forwards: the reaction after a crash is the part people clip.
        if after and (not before or (hi - last) <= (first - lo)):
            hi += 1
        else:
            lo -= 1
    span = segments[hi].end - segments[lo].start
    if span > max_s or span < min_s:
        return None
    return lo, hi


def overlaps_proposed(moment: Moment, proposed: list[tuple[float, float]]) -> bool:
    """Whether the model already proposed this moment (pure)."""
    return any(
        moment.start < end + SAME_MOMENT_SECONDS and start - SAME_MOMENT_SECONDS < moment.end
        for start, end in proposed
    )


def action_ranges(
    moments: list[Moment],
    segments: list[Segment],
    proposed: list[tuple[float, float]],
    min_s: float,
    max_s: float,
    limit: int = MAX_ACTION_CANDIDATES,
) -> list[ActionRange]:
    """Loud moments the model missed, as segment ranges it can score (pure).

    Strongest first, de-duplicated against each other and against what was already proposed.
    """
    out: list[ActionRange] = []
    claimed: list[tuple[float, float]] = list(proposed)
    for moment in sorted(moments, key=lambda m: m.above_median_db, reverse=True):
        if len(out) >= limit:
            break
        if overlaps_proposed(moment, claimed):
            continue
        covered = segments_covering(segments, moment.start, moment.end)
        if covered is None:
            # Nobody spoke over it. Without segments there is nothing to caption, cut or
            # score, so it is left alone rather than guessed at.
            continue
        first, last = covered
        if not fits(segments, first, last, min_s, max_s):
            grown = grow(segments, first, last, min_s, max_s)
            if grown is None:
                continue
            first, last = grown
        claimed.append((segments[first].start, segments[last].end))
        out.append(
            ActionRange(
                start_segment=first,
                end_segment=last,
                above_median_db=round(moment.above_median_db, 1),
                text=" ".join(s.text for s in segments[first : last + 1])[:600],
            )
        )
    return out
