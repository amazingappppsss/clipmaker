"""pipeline/transcript.py + pipeline/selection.py — the editorial rules, tested in isolation."""

from __future__ import annotations

import pytest

from clipmaker.pipeline.selection import (
    SIGNALS,
    Proposal,
    auto_clip_count,
    clip_times,
    gate_failure,
    normalise_range,
    overlap_fraction,
    parse_weights,
    pick_teaser,
    select_clips,
    strengths,
    weighted_score,
)
from clipmaker.pipeline.transcript import Segment, build_segments, render_for_llm
from clipmaker.providers.transcription.base import Word
from pipeline_fakes import fake_words


def _w(text: str, start: float, speaker: str = "A") -> Word:
    return Word(text=text, start=start, end=start + 0.3, speaker=speaker)


def _segments(lengths: list[float], gap: float = 0.5) -> list[Segment]:
    segs, t = [], 0.0
    for i, length in enumerate(lengths):
        segs.append(Segment(idx=i, start=t, end=t + length, speaker="A", words=[_w(f"s{i}.", t)]))
        t += length + gap
    return segs


# --- segmentation ---------------------------------------------------------------------
def test_splits_on_punctuation_speaker_and_pause() -> None:
    words = [
        _w("Hello", 0.0),
        _w("there.", 0.4),  # punctuation
        _w("And", 0.8),
        _w("then", 1.1),  # long pause next
        _w("silence", 3.0),
        _w("Hi", 3.4, speaker="B"),  # speaker change
    ]
    segs = build_segments(words)
    assert [s.text for s in segs] == ["Hello there.", "And then", "silence", "Hi"]
    assert [s.speaker for s in segs] == ["A", "A", "A", "B"]
    assert segs[0].start == 0.0 and segs[0].end == pytest.approx(0.7)


def test_run_on_speech_is_capped() -> None:
    words = [_w(f"w{i}", i * 0.3) for i in range(100)]
    assert max(len(s.words) for s in build_segments(words)) <= 45


def test_render_is_deterministic_and_indexed() -> None:
    segs = build_segments(fake_words(repeats=1))
    text = render_for_llm(segs)
    assert text == render_for_llm(segs)
    assert text.splitlines()[0].startswith("[S0 | 00:00.5-")
    assert "Speaker B" in text


# --- scoring ----------------------------------------------------------------------------
def test_weights_normalise_and_reject_unknown() -> None:
    w = parse_weights('{"standalone": 2, "hook": 2}')
    assert w["standalone"] == pytest.approx(0.5)
    assert w["payoff"] == 0
    with pytest.raises(ValueError):
        parse_weights('{"virality": 1}')


def test_weighted_score_clamps() -> None:
    w = parse_weights('{"standalone": 1}')
    assert weighted_score({"standalone": 10}, w) == 100
    assert weighted_score({"standalone": 99}, w) == 100
    assert weighted_score({}, w) == 0


@pytest.mark.parametrize(("minutes", "count"), [(2, 3), (5, 3), (10, 7), (15, 10), (120, 12)])
def test_auto_clip_count(minutes: int, count: int) -> None:
    assert auto_clip_count(minutes * 60) == count


# --- boundaries -------------------------------------------------------------------------
def test_too_long_is_trimmed_at_sentence_boundary() -> None:
    segs = _segments([30, 30, 30, 30])  # 3 sentences + gaps = 91s, just over the limit
    s, e, adjusted, reason = normalise_range(segs, 0, 3, 20, 90)
    assert reason is None and adjusted
    assert (s, e) == (0, 1)


def test_too_short_is_extended() -> None:
    segs = _segments([5, 5, 5, 5, 5])
    s, e, adjusted, reason = normalise_range(segs, 1, 1, 20, 90)
    assert reason is None and adjusted and segs[e].end - segs[s].start >= 20


def test_single_overlong_sentence_rejected() -> None:
    segs = _segments([120])
    assert normalise_range(segs, 0, 0, 20, 90)[3] is not None


def test_clip_times_never_bleed_into_neighbours() -> None:
    segs = _segments([10, 10, 10], gap=0.1)
    start, end = clip_times(segs, 1, 1)
    assert start >= segs[0].end and end <= segs[2].start


def test_overlap_fraction() -> None:
    assert overlap_fraction((0, 10), (5, 30)) == 0.5
    assert overlap_fraction((0, 10), (20, 30)) == 0


# --- selection --------------------------------------------------------------------------
def _p(start: int, end: int, score: float) -> Proposal:
    return Proposal(start, end, "story", "r", "h", {s: score for s in SIGNALS})


def test_select_dedupes_ranks_and_applies_quality_bar() -> None:
    segs = _segments([10] * 30)
    weights = parse_weights('{"standalone": 1}')
    proposals = [_p(0, 3, 9), _p(1, 4, 8), _p(10, 13, 7), _p(20, 23, 3)]
    result = select_clips(
        proposals, segs, weights, target_count=5, min_s=20, max_s=90, min_score=55
    )
    chosen = [c for c in result if c.selected]
    assert [c.total_score for c in chosen] == [90, 70]
    reasons = {c.proposal.scores["standalone"]: c.rejected_reason for c in result}
    assert reasons[8] == "overlaps a stronger moment"
    assert reasons[3] == "needs outside context to make sense"


def test_select_respects_target_count() -> None:
    segs = _segments([10] * 40)
    weights = parse_weights('{"standalone": 1}')
    proposals = [_p(i * 5, i * 5 + 3, 9 - i * 0.1) for i in range(8)]
    result = select_clips(
        proposals, segs, weights, target_count=3, min_s=20, max_s=90, min_score=55
    )
    assert sum(c.selected for c in result) == 3


def test_best_moment_kept_even_below_bar_but_flagged() -> None:
    segs = _segments([10] * 10)
    weights = parse_weights('{"standalone": 1}')
    result = select_clips(
        [_p(0, 3, 4)], segs, weights, target_count=3, min_s=20, max_s=90, min_score=55
    )
    assert result[0].selected and result[0].notes


def test_gates_reject_clips_without_payoff_or_context() -> None:
    good = {s: 7.0 for s in SIGNALS}
    assert gate_failure(good) is None
    assert gate_failure({**good, "payoff": 2}) == "ends without a payoff"
    assert gate_failure({**good, "standalone": 3}) == "needs outside context to make sense"
    assert gate_failure({**good, "hook": 1}) == "opening won't stop the scroll"


def test_near_the_bar_fills_up_to_three() -> None:
    segs = _segments([10] * 40)
    weights = parse_weights('{"standalone": 1}')
    proposals = [_p(0, 3, 8), _p(10, 13, 4.5), _p(20, 23, 4.5), _p(30, 33, 4.5)]
    result = select_clips(
        proposals, segs, weights, target_count=6, min_s=20, max_s=90, min_score=55
    )
    assert sum(c.selected for c in result) == 3  # 1 above the bar + 2 close to it


def test_strengths_are_creator_friendly() -> None:
    scores = {s: 5.0 for s in SIGNALS} | {"hook": 9, "transformation": 8, "payoff": 7.5}
    assert strengths(scores) == ["Scroll-stopping hook", "Someone changes", "Strong payoff"]


def test_prompt_version_fits_its_column() -> None:
    from clipmaker.pipeline.prompts import PROMPT_VERSION

    assert len(PROMPT_VERSION) <= 20


def test_teaser_must_be_inside_short_and_not_the_payoff() -> None:
    segs = _segments([10, 3, 3, 10, 4])  # S1-S2 short lines, S4 is the last (payoff) line
    assert pick_teaser(segs, 0, 4, 2) == (2, segs[2].start, segs[2].end)
    assert pick_teaser(segs, 0, 4, 0) is None  # the first line already plays first
    assert pick_teaser(segs, 0, 4, 4) is None  # never spoil the payoff
    assert pick_teaser(segs, 0, 4, 3) is None  # 10 s is too long for a hook
    assert pick_teaser(segs, 0, 4, -1) is None  # model chose no teaser


def test_long_clips_must_earn_their_length() -> None:
    from clipmaker.pipeline.selection import length_penalty

    assert length_penalty(30, 35) == 0
    assert length_penalty(45, 35) == 6
    segs = _segments([10] * 40)
    weights = parse_weights('{"standalone": 1}')
    # Same quality, different lengths: the tight clip must win.
    short, long_ = _p(0, 2, 8), _p(10, 15, 8)
    result = select_clips(
        [long_, short], segs, weights, 1, min_s=12, max_s=60, min_score=55, ideal_max=35
    )
    chosen = [c for c in result if c.selected]
    assert chosen[0].proposal is short


def test_clip_keeps_the_other_persons_quick_reaction() -> None:
    from dataclasses import replace

    from clipmaker.pipeline.selection import include_reaction

    segs = _segments([10, 10, 2, 10])
    segs[2] = replace(segs[2], speaker="B")  # "No way!" from the other speaker
    assert include_reaction(segs, 0, 1, max_s=60) == 2
    assert include_reaction(segs, 0, 1, max_s=21) == 1  # would exceed the max length
    same = _segments([10, 10, 2, 10])  # same speaker continuing: not a reaction
    assert include_reaction(same, 0, 1, max_s=60) == 1
    long_reply = _segments([10, 10, 8, 10])
    long_reply[2] = replace(long_reply[2], speaker="B")  # a new turn, not a reaction
    assert include_reaction(long_reply, 0, 1, max_s=60) == 1
