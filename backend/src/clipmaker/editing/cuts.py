"""Smart cuts: remove filler and dead air, keep the rhythm. Pure functions, unit-tested.

Editors cut filler and long pauses (4-8 cuts a minute is typical) but keep the speaker's
natural cadence, and they never rush the beat right before a reveal (Storyworthy's
"hourglass"). We work from word timestamps: words separated by less than MAX_GAP stay
together; longer gaps are tightened to KEEP_GAP; the pause right before the protected
"five-second moment" is kept up to HOURGLASS_GAP.

Filler is cut as well as silence, which is the loudest difference between a raw clip and an
edited one. A dropped word becomes part of the gap around it, so the same tightening removes
it from the picture and `map_words` drops it from the captions — one rule, both places.
"""

from __future__ import annotations

from dataclasses import dataclass

from clipmaker.providers.transcription.base import Word

#: Sounds, not words. Cut on their own, never as part of a phrase that means something.
FILLERS = frozenset(
    {
        "um",
        "umm",
        "ummm",
        "uh",
        "uhh",
        "uhhh",
        "er",
        "erm",
        "ah",
        "ahh",
        "hmm",
        "hmmm",
        "mhm",
        "mm",
        "mmm",
        "eh",
        "huh",
    }
)
#: A stammer worth cutting only if it repeats immediately and quickly: "I- I- I think".
#: Deliberate repetition for effect ("no. no. no.") is slower than this and survives.
STUTTER_GAP = 0.5

MAX_GAP = 0.45  # silences longer than this are tightened
KEEP_GAP = 0.12  # breathing room left on each side of a cut
#: Breathing room around a *filler* cut. Deliberately tiny: KEEP_GAP on both sides of a
#: dropped "um" puts back more time than the "um" took, so the clip gets longer instead of
#: tighter. Just enough not to clip the next word's attack.
FILLER_KEEP = 0.03
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


def _bare(text: str) -> str:
    """A word with punctuation and case stripped, for comparing."""
    return text.strip().strip(".,!?;:-\u2014\u2013'\"").lower()


def is_filler(word: Word, previous: Word | None) -> bool:
    """Whether this word is noise we should cut (pure).

    Two kinds: a filler sound on its own, and an immediate stammer — the same word repeated
    within STUTTER_GAP. The repeat is dropped, not the word, so the sentence survives.
    """
    bare = _bare(word.text)
    if not bare:
        return False
    if bare in FILLERS:
        return True
    if previous is not None and _bare(previous.text) == bare:
        return word.start - previous.end < STUTTER_GAP
    return False


def strip_filler(words: list[Word]) -> tuple[list[Word], set[int]]:
    """Speech without the filler, and the indexes into it after which something was cut."""
    kept: list[Word] = []
    cut_after: set[int] = set()
    for word in words:
        if is_filler(word, kept[-1] if kept else None):
            if kept:
                cut_after.add(len(kept) - 1)
            continue
        kept.append(word)
    return kept, cut_after


def keep_intervals(
    words: list[Word],
    start: float,
    end: float,
    protect_before: float | None = None,
) -> list[Interval]:
    """Stretches of [start, end] to keep, with filler removed and long silences tightened.

    `protect_before`: source time where the reveal line begins; the pause before it is kept
    (up to HOURGLASS_GAP) instead of being cut tight.
    """
    within = [w for w in words if w.end > start and w.start < end]
    inside, cut_after = strip_filler(within)
    if not inside:
        return [Interval(start, end)] if end > start else []
    out: list[Interval] = []
    cur_start = max(start, inside[0].start - LEAD)
    prev_end = inside[0].end
    for index, w in enumerate(inside[1:]):
        gap = w.start - prev_end
        limit = MAX_GAP
        if protect_before is not None and abs(w.start - protect_before) < 0.05:
            limit = HOURGLASS_GAP
        # A dropped filler always forces a cut, however short the gap around it reads —
        # otherwise the word stays in the picture and only leaves the captions.
        dropped_filler = index in cut_after
        if gap > limit or dropped_filler:
            if limit != MAX_GAP:
                keep = HOURGLASS_GAP / 2
            elif dropped_filler:
                keep = FILLER_KEEP
            else:
                keep = KEEP_GAP
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
