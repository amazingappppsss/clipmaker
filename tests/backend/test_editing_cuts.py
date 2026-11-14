"""editing/cuts.py — dead air out, rhythm and reveal pauses kept, timeline mapping."""

from __future__ import annotations

import itertools

from clipmaker.editing.cuts import (
    HOURGLASS_GAP,
    Interval,
    keep_intervals,
    map_time,
    map_words,
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
