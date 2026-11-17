"""Clips found by sound rather than by words — the gameplay path.

Every editorial signal we had read a transcript, so a crash scoring 9 for emotion was still
rejected for "needing outside context": nobody narrated it. These cover the bridge from a
measured loud moment to a candidate, and the gates that then apply to it.
"""

from __future__ import annotations

from clipmaker.editing.energy import Moment
from clipmaker.pipeline.action import (
    SAME_MOMENT_SECONDS,
    action_ranges,
    grow,
    overlaps_proposed,
    segments_covering,
)
from clipmaker.pipeline.selection import ACTION, SPEECH, gate_failure
from clipmaker.pipeline.transcript import Segment
from clipmaker.providers.transcription.base import Word


def _seg(idx: int, start: float, end: float, text: str = "oh my god") -> Segment:
    span = (end - start) / max(1, len(text.split()))
    words = [
        Word(text=t, start=start + i * span, end=start + (i + 1) * span, speaker="A")
        for i, t in enumerate(text.split())
    ]
    return Segment(idx=idx, start=start, end=end, speaker="A", words=words)


def _moment(start: float, end: float, db: float = 9.0) -> Moment:
    return Moment(start=start, end=end, peak_db=-8.0, above_median_db=db)


# --- gates ----------------------------------------------------------------------------------
def test_a_gameplay_moment_is_no_longer_rejected_for_having_no_narration() -> None:
    """The exact case that failed: emotion 9, momentum 7, share 7, nothing quotable."""
    crash = {
        "emotion": 9.0,
        "momentum": 7.0,
        "share_trigger": 7.0,
        "standalone": 2.0,
        "payoff": 2.0,
        "hook": 2.0,
    }
    assert gate_failure(crash, SPEECH) == "needs outside context to make sense"
    assert gate_failure(crash, ACTION) is None


def test_a_loud_moment_nobody_reacts_to_still_does_not_ship() -> None:
    """Relaxing the gates must not mean every bang becomes a clip."""
    flat = {"emotion": 3.0, "share_trigger": 6.0, "momentum": 8.0}
    assert gate_failure(flat, ACTION) == "loud, but nothing happens worth reacting to"
    unshareable = {"emotion": 8.0, "share_trigger": 2.0}
    assert gate_failure(unshareable, ACTION) == "no reason anybody would send it on"


def test_speech_clips_keep_the_gates_they_had() -> None:
    good = dict.fromkeys(("standalone", "payoff", "hook", "emotion", "share_trigger"), 8.0)
    assert gate_failure(good, SPEECH) is None
    assert gate_failure({**good, "payoff": 1.0}, SPEECH) == "ends without a payoff"


# --- seconds to segments --------------------------------------------------------------------
def test_a_stretch_of_seconds_maps_to_the_segments_it_overlaps() -> None:
    segments = [_seg(0, 0.0, 10.0), _seg(1, 10.0, 20.0), _seg(2, 20.0, 30.0)]
    assert segments_covering(segments, 12.0, 18.0) == (1, 1)
    assert segments_covering(segments, 8.0, 22.0) == (0, 2)
    # Touching an edge is not overlapping it.
    assert segments_covering(segments, 10.0, 20.0) == (1, 1)


def test_a_moment_in_silence_maps_to_nothing() -> None:
    """Without segments there is nothing to caption, cut or score, so it is left alone."""
    segments = [_seg(0, 0.0, 5.0), _seg(1, 60.0, 65.0)]
    assert segments_covering(segments, 20.0, 30.0) is None
    assert segments_covering([], 1.0, 2.0) is None


def test_a_short_moment_grows_to_a_usable_clip_length() -> None:
    segments = [_seg(i, i * 5.0, i * 5.0 + 5.0) for i in range(8)]
    grown = grow(segments, 3, 3, min_s=12.0, max_s=75.0)
    assert grown is not None
    first, last = grown
    assert segments[last].end - segments[first].start >= 12.0
    assert first <= 3 <= last, "the moment must stay inside the clip"


def test_a_moment_that_cannot_reach_the_minimum_length_is_dropped() -> None:
    """A 6 s recording has no 12 s clip in it, however loud it got."""
    assert grow([_seg(0, 0.0, 6.0)], 0, 0, min_s=12.0, max_s=75.0) is None


def test_growing_never_exceeds_the_maximum_length() -> None:
    segments = [_seg(0, 0.0, 40.0), _seg(1, 40.0, 80.0)]
    assert grow(segments, 0, 1, min_s=12.0, max_s=75.0) is None


# --- de-duplication ------------------------------------------------------------------------
def test_a_moment_the_model_already_proposed_is_not_offered_twice() -> None:
    proposed = [(100.0, 140.0)]
    assert overlaps_proposed(_moment(120.0, 125.0), proposed) is True
    assert overlaps_proposed(_moment(141.0, 146.0), proposed) is True, "within the grace window"
    assert overlaps_proposed(_moment(200.0, 205.0), proposed) is False
    assert overlaps_proposed(_moment(140.0 + SAME_MOMENT_SECONDS + 1, 150.0), proposed) is False


def test_the_loudest_moments_come_first_and_do_not_overlap_each_other() -> None:
    segments = [_seg(i, i * 10.0, i * 10.0 + 10.0) for i in range(12)]
    moments = [
        _moment(5.0, 20.0, db=7.0),
        _moment(8.0, 22.0, db=14.0),  # same stretch, louder: this one wins
        _moment(95.0, 110.0, db=9.0),
    ]
    found = action_ranges(moments, segments, [], min_s=12.0, max_s=75.0)
    assert [r.above_median_db for r in found] == [14.0, 9.0]
    assert found[0].text, "the words shouted over it ride along for scoring"


def test_nothing_is_proposed_for_a_video_with_no_loud_moments() -> None:
    segments = [_seg(i, i * 10.0, i * 10.0 + 10.0) for i in range(4)]
    assert action_ranges([], segments, [], min_s=12.0, max_s=75.0) == []


def test_the_candidate_count_is_capped() -> None:
    segments = [_seg(i, i * 10.0, i * 10.0 + 10.0) for i in range(60)]
    moments = [_moment(i * 40.0 + 5.0, i * 40.0 + 20.0, db=8.0 + i) for i in range(20)]
    assert len(action_ranges(moments, segments, [], min_s=12.0, max_s=75.0, limit=5)) == 5


# --- the model's answer --------------------------------------------------------------------
def test_scores_are_matched_by_the_index_we_gave_not_by_order() -> None:
    from clipmaker.pipeline.stages.select import parse_action_scores

    data = {
        "moments": [
            {"index": 1, "title": "second", "scores": {"emotion": 9}},
            {"index": 0, "title": "first", "scores": {"emotion": 4}},
        ]
    }
    parsed = parse_action_scores(data, 2)
    assert parsed[0]["title"] == "first"
    assert parsed[1]["scores"]["emotion"] == 9.0


def test_a_malformed_or_out_of_range_answer_is_skipped_not_trusted() -> None:
    from clipmaker.pipeline.stages.select import parse_action_scores

    data = {
        "moments": [
            {"index": 7, "scores": {"emotion": 9}},  # no such moment
            {"index": 0},  # no scores
            "nonsense",
            {"index": 1, "scores": {"emotion": 8}},
        ]
    }
    assert sorted(parse_action_scores(data, 2)) == [1]


def test_the_model_is_told_the_loudness_and_the_words_if_any() -> None:
    from clipmaker.pipeline.action import ActionRange
    from clipmaker.pipeline.stages.select import describe_moments

    text = describe_moments(
        [
            ActionRange(0, 2, 11.0, "oh my god"),
            ActionRange(5, 7, 8.0, "   "),
        ]
    )
    assert "[0] +11 dB" in text
    assert "oh my god" in text
    assert "(nothing)" in text, "silence must be stated, not left as an empty line"
