"""The clip report card — the benchmark we were editing without."""

from __future__ import annotations

from typing import Any

from clipmaker.editing.report import (
    caption_coverage,
    dead_air_ratio,
    ends_mid_sentence,
    filler_left,
    opens_cold,
    report,
    shot_seconds,
    summarise,
)


def _plan(words: list[tuple[str, float, float]], duration: float, **extra: Any) -> dict[str, Any]:
    return {
        "words": [list(w) for w in words],
        "duration": duration,
        "pieces": extra.pop("pieces", [{"start": 0.0, "end": duration}]),
        **extra,
    }


def _speech(count: int, start: float = 0.0, rate: float = 0.35) -> list[tuple[str, float, float]]:
    """A run of evenly spoken words, the last one ending a sentence."""
    out = []
    t = start
    for i in range(count):
        text = "word." if i == count - 1 else "word"
        out.append((text, round(t, 2), round(t + rate * 0.9, 2)))
        t += rate
    return out


def test_dead_air_is_measured_as_a_share_of_the_clip() -> None:
    words = [("one", 0.0, 0.4), ("two", 3.0, 3.4)]  # a 2.6s hole in a 4s clip
    assert dead_air_ratio(words, 4.0) == 0.65
    assert dead_air_ratio(_speech(10), 3.5) == 0.0
    assert dead_air_ratio([], 10.0) == 0.0, "no words is not dead air, it is no data"


def test_caption_coverage_is_how_much_of_the_clip_has_words_on_screen() -> None:
    assert caption_coverage([("a", 0.0, 5.0)], 10.0) == 0.5
    assert caption_coverage([], 10.0) == 0.0
    # Overlapping or over-long spans cannot exceed the clip.
    assert caption_coverage([("a", 0.0, 20.0)], 10.0) == 1.0


def test_filler_that_survived_the_cut_is_reported() -> None:
    assert filler_left([("So", 0, 0.2), ("um", 0.3, 0.5)]) == ["um"]
    assert filler_left(_speech(5)) == []
    assert filler_left([("umbrella", 0, 0.4)]) == [], "a word is not a filler sound"


def test_a_clip_opening_on_a_dangling_word_is_flagged() -> None:
    assert opens_cold([("So", 0, 0.2), ("I", 0.3, 0.4)]) is True
    assert opens_cold([("Because", 0, 0.4)]) is True
    assert opens_cold([("Nobody", 0, 0.4)]) is False
    assert opens_cold([]) is True


def test_an_unfinished_last_sentence_is_flagged() -> None:
    assert ends_mid_sentence([("and", 0, 0.3)]) is True
    assert ends_mid_sentence([("back.", 0, 0.4)]) is False
    assert ends_mid_sentence([("really?", 0, 0.4)]) is False


def test_shot_lengths_come_from_the_render_pieces() -> None:
    plan = _plan([], 10.0, pieces=[{"start": 0, "end": 4}, {"start": 4, "end": 10}])
    assert shot_seconds(plan) == [4.0, 6.0]
    assert shot_seconds({"pieces": [{"start": 2, "end": 2}]}) == [], "a zero-length shot is not one"


def test_a_good_clip_passes_everything() -> None:
    words = _speech(90)  # 90 words over ~31.5s: comfortably conversational
    plan = _plan(
        words,
        31.5,
        pieces=[
            {"start": 0, "end": 8},
            {"start": 8, "end": 18},
            {"start": 18, "end": 26},
            {"start": 26, "end": 31.5},
        ],
    )
    plan["words"][0][0] = "Nobody"
    summary = summarise(report(plan))
    assert summary["missed"] == [], summary["missed"]
    assert summary["passed"] == summary["checks"]


def test_the_report_names_what_is_wrong_rather_than_scoring_it() -> None:
    """A score we cannot check is the unproven number we criticise others for."""
    words = [("So", 0.0, 0.3), ("um", 0.4, 0.6), ("yeah", 8.0, 8.4)]
    plan = _plan(words, 40.0, pieces=[{"start": 0, "end": 40}])
    missed = {m["key"] for m in summarise(report(plan))["missed"]}
    assert {"dead_air", "pace", "filler", "captions", "framing", "opening", "ending"} <= missed
    notes = {m["key"]: m["note"] for m in summarise(report(plan))["missed"]}
    assert "um" in notes["filler"]
    assert "40s" in notes["framing"], "a frame held for the whole clip should say so"


def test_an_empty_plan_does_not_crash() -> None:
    """Older plans and failed renders still have to be reportable."""
    summary = summarise(report({}))
    assert summary["checks"] > 0
    assert summary["passed"] >= 0
