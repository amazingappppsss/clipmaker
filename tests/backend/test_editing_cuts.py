"""editing/cuts.py — dead air out, rhythm and reveal pauses kept, timeline mapping."""

from __future__ import annotations

import itertools

from clipmaker.editing.cuts import (
    HOURGLASS_GAP,
    Interval,
    is_filler,
    keep_intervals,
    map_time,
    map_words,
    strip_filler,
    total_duration,
)
from clipmaker.providers.transcription.base import Word


def _w(text: str, start: float, end: float) -> Word:
    return Word(text, start, end)


WORDS = [
    _w("So", 10.0, 10.2),
    _w("I", 10.3, 10.4),  # 0.1 s gap: natural rhythm, kept
    _w("quit.", 10.5, 10.9),
    _w("Then", 13.0, 13.3),  # 2.1 s dead air: tightened
    _w("everything", 13.4, 13.9),
    _w("changed.", 14.0, 14.5),
]


def test_dead_air_is_cut_but_rhythm_kept() -> None:
    kept = keep_intervals(WORDS, 9.5, 15.0)
    assert len(kept) == 2
    assert kept[0].start < 10.0 and kept[0].end < 11.2
    assert kept[1].start > 12.5
    assert total_duration(kept) < 5.0 - 1.5  # ~2 s of silence removed


def test_reveal_pause_is_protected() -> None:
    plain = keep_intervals(WORDS, 9.5, 15.0)
    protected = keep_intervals(WORDS, 9.5, 15.0, protect_before=13.0)
    added = total_duration(protected) - total_duration(plain)
    assert 0 < added <= HOURGLASS_GAP


def test_times_map_onto_the_cut_timeline() -> None:
    kept = [Interval(10, 11), Interval(13, 15)]
    assert map_time(10.5, kept) == 0.5
    assert map_time(13.5, kept) == 1.5
    assert map_time(12.0, kept) is None  # inside a removed gap
    assert map_time(10.5, kept, offset=3.0) == 3.5
    mapped = map_words(WORDS, keep_intervals(WORDS, 9.5, 15.0))
    assert [w.text for w in mapped] == [w.text for w in WORDS]
    assert all(b.start >= a.end - 1e-6 for a, b in itertools.pairwise(mapped))


def test_no_words_keeps_the_whole_range() -> None:
    assert keep_intervals([], 5.0, 8.0) == [Interval(5.0, 8.0)]


def test_filler_sounds_are_cut_not_just_silence() -> None:
    """The loudest difference between a raw clip and an edited one."""
    words = [
        Word("So", 0.0, 0.2),
        Word("um", 0.25, 0.45),
        Word("I", 0.5, 0.6),
        Word("left.", 0.65, 1.0),
    ]
    kept, cut_after = strip_filler(words)
    assert [w.text for w in kept] == ["So", "I", "left."]
    assert cut_after == {0}, "the cut belongs after the word that preceded the filler"
    assert is_filler(Word("uh", 0, 0.1), None)
    assert not is_filler(Word("I", 0, 0.1), None)


def test_a_word_that_merely_contains_a_filler_is_kept() -> None:
    for text in ("umbrella", "under", "ahead", "human"):
        assert not is_filler(Word(text, 0, 0.3), None), text


def test_an_immediate_stammer_loses_the_repeat_not_the_word() -> None:
    kept, _ = strip_filler([Word("I", 0.0, 0.1), Word("I", 0.15, 0.25), Word("think", 0.3, 0.6)])
    assert [w.text for w in kept] == ["I", "think"]


def test_deliberate_repetition_survives() -> None:
    """ "No. No. No." said slowly is a performance, not a stammer."""
    kept, _ = strip_filler([Word("No.", 0.0, 0.3), Word("No.", 1.0, 1.3), Word("No.", 2.0, 2.3)])
    assert len(kept) == 3


def test_filler_is_cut_from_the_picture_even_when_the_gap_is_small() -> None:
    """Dropping it from the captions alone would leave the mouth moving with no words."""
    words = [
        Word("So", 0.0, 0.2),
        Word("um", 0.22, 0.42),
        Word("I", 0.44, 0.55),
        Word("left.", 0.57, 1.0),
    ]
    intervals = keep_intervals(words, 0.0, 1.2)
    assert len(intervals) > 1, "no cut was made, so the filler is still on screen"
    kept = sum(i.duration for i in intervals)
    assert kept < 1.2, "the clip should be shorter than the raw range"
    # The filler's own time is not inside any kept interval.
    assert not any(i.start <= 0.32 <= i.end for i in intervals)
