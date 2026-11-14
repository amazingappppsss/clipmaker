"""Smart cuts: remove dead air between words, keep the rhythm. Pure functions, unit-tested.

Editors cut filler and long pauses (4-8 cuts a minute is typical) but keep the speaker's
natural cadence, and they never rush the beat right before a reveal (Storyworthy's
"hourglass"). We work from word timestamps: words separated by less than MAX_GAP stay
together; longer gaps are tightened to KEEP_GAP; the pause right before the protected
"five-second moment" is kept up to HOURGLASS_GAP.
"""

from __future__ import annotations

from dataclasses import dataclass

from clipmaker.providers.transcription.base import Word

MAX_GAP = 0.45  # silences longer than this are tightened
KEEP_GAP = 0.12  # breathing room left on each side of a cut
HOURGLASS_GAP = 0.9  # pause kept before the reveal line
LEAD = 0.08  # before the first word
TAIL = 0.30  # after the last word (let it ring out)


@dataclass(frozen=True, slots=True)
class Interval:
    """A kept stretch of the source video, in source seconds."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def keep_intervals(
    words: list[Word],
    start: float,
    end: float,
    protect_before: float | None = None,
) -> list[Interval]:
    """Stretches of [start, end] to keep, with long silences tightened.

    `protect_before`: source time where the reveal line begins; the pause before it is kept
    (up to HOURGLASS_GAP) instead of being cut tight.
    """
    inside = [w for w in words if w.end > start and w.start < end]
    if not inside:
        return [Interval(start, end)] if end > start else []
    out: list[Interval] = []
    cur_start = max(start, inside[0].start - LEAD)
    prev_end = inside[0].end
    for w in inside[1:]:
        gap = w.start - prev_end
        limit = MAX_GAP
        if protect_before is not None and abs(w.start - protect_before) < 0.05:
            limit = HOURGLASS_GAP
        if gap > limit:
            keep = KEEP_GAP if limit == MAX_GAP else HOURGLASS_GAP / 2
            out.append(Interval(cur_start, prev_end + keep))
            cur_start = w.start - keep
        prev_end = max(prev_end, w.end)
    out.append(Interval(cur_start, min(end, prev_end + TAIL)))
    return [i for i in out if i.duration > 0.05]


def total_duration(intervals: list[Interval]) -> float:
    return round(sum(i.duration for i in intervals), 3)


def map_time(t: float, intervals: list[Interval], offset: float = 0.0) -> float | None:
    """Source time → output time after cutting (None if `t` falls in a removed gap)."""
    elapsed = offset
    for i in intervals:
        if i.start <= t <= i.end:
            return round(elapsed + (t - i.start), 3)
        elapsed += i.duration
    return None


def map_words(words: list[Word], intervals: list[Interval], offset: float = 0.0) -> list[Word]:
    """Words re-timed onto the output timeline (words in removed gaps are dropped)."""
    out: list[Word] = []
    for w in words:
        s = map_time(w.start, intervals, offset)
        e = map_time(w.end, intervals, offset)
        if s is None or e is None or e <= s:
            continue
        out.append(Word(w.text, s, e, w.confidence, w.speaker))
    return out
