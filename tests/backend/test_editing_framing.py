"""editing/framing.py — speaker following, punch-ins, crop geometry."""

from __future__ import annotations

from clipmaker.editing.cuts import Interval
from clipmaker.editing.framing import (
    Face,
    Sample,
    Shot,
    crop_box,
    plan_shots,
    turns_from_words,
)
from clipmaker.providers.transcription.base import Word


def _two_people(switch_at: float, until: float) -> list[Sample]:
    """Host on the left talks first, guest on the right after `switch_at`."""
    out = []
    t = 0.0
    while t <= until:
        left_talks = t < switch_at
        out.append(
            Sample(
                t,
                [
                    Face(0.3, 0.4, 0.1, motion=9.0 if left_talks else 0.5),
                    Face(0.7, 0.4, 0.1, motion=0.5 if left_talks else 9.0),
                ],
            )
        )
        t += 0.25
    return out


def test_frame_follows_whoever_is_talking_without_a_transcript() -> None:
    shots = plan_shots(_two_people(switch_at=4.0, until=8.0), [Interval(0, 8)])
    assert abs(shots[0].cx - 0.3) < 0.05
    assert abs(shots[-1].cx - 0.7) < 0.05


def test_one_framing_per_turn_with_no_restless_zooming() -> None:
    samples = [Sample(t / 4, [Face(0.5, 0.4, 0.1, motion=5)]) for t in range(0, 4 * 20)]
    shots = plan_shots(samples, [Interval(0, 20)])
    assert {s.zoom for s in shots} == {1.0}  # the crop never resizes mid-clip
    assert len(shots) == 1  # one speaker, one steady framing


def test_no_faces_means_steady_centre() -> None:
    shots = plan_shots([], [Interval(0, 4)])
    assert all(abs(s.cx - 0.5) < 1e-9 for s in shots)


def test_crop_is_9_16_and_inside_the_frame() -> None:
    x, y, w, h = crop_box(1920, 1080, Shot(0, 1, cx=0.98, cy=0.5))
    assert (w, h) == (606, 1080) and x + w <= 1920 and x >= 0
    x, y, w, h = crop_box(1920, 1080, Shot(0, 1, cx=0.5, cy=0.4))
    assert abs(w / h - 9 / 16) < 0.01 and y >= 0 and y + h <= 1080
    assert crop_box(1080, 1920, Shot(0, 1, 0.5, 0.5)) == (0, 0, 1080, 1920)  # already vertical


# --- diarisation-driven framing -------------------------------------------------------------
def _word(text: str, start: float, end: float, speaker: str) -> Word:
    return Word(text, start, end, 1.0, speaker)


def _two_faces(until: float, left_motion_when: tuple[float, float]) -> list[Sample]:
    """Two people on screen; the left one's mouth moves only inside `left_motion_when`."""
    out, t = [], 0.0
    while t <= until:
        left_talks = left_motion_when[0] <= t <= left_motion_when[1]
        out.append(
            Sample(
                t,
                [
                    Face(0.28, 0.4, 0.1, 0.13, motion=9.0 if left_talks else 0.4),
                    Face(0.72, 0.4, 0.1, 0.13, motion=0.4 if left_talks else 9.0),
                ],
            )
        )
        t += 0.25
    return out


def test_turns_ignore_short_interjections() -> None:
    words = [
        _word("I", 0.0, 1.0, "A"),
        _word("think", 1.0, 4.0, "A"),
        _word("yeah", 4.1, 4.6, "B"),  # a half-second "yeah" is not a reason to cut away
        _word("so", 4.7, 8.0, "A"),
        _word("actually", 8.1, 12.0, "B"),  # a real turn
    ]
    turns = turns_from_words(words)
    assert [t.speaker for t in turns] == ["A", "B"]
    assert turns[0].start == 0.0 and turns[1].end == 12.0


def test_camera_follows_the_diarised_speaker() -> None:
    samples = _two_faces(12.0, left_motion_when=(0.0, 6.0))
    words = [_word("hi", 0.0, 6.0, "A"), _word("no", 6.1, 12.0, "B")]
    shots = plan_shots(samples, [Interval(0, 12)], words)
    assert abs(shots[0].cx - 0.28) < 0.05  # speaker A is on the left
    assert abs(shots[-1].cx - 0.72) < 0.05  # cuts to B when B takes over
    assert all(s.face_h > 0 for s in shots)


def test_framing_holds_steady_when_speakers_cannot_be_told_apart() -> None:
    """One face, two voices (off-camera guest): a steady frame beats cutting to the wrong person."""
    samples = [Sample(t / 4, [Face(0.5, 0.4, 0.1, 0.13, motion=5)]) for t in range(0, 4 * 12)]
    words = [_word("hi", 0.0, 6.0, "A"), _word("no", 6.1, 12.0, "B")]
    shots = plan_shots(samples, [Interval(0, 12)], words)
    assert {round(s.cx, 2) for s in shots} == {0.5}


def test_head_is_never_cut_off() -> None:
    tall = Shot(0, 1, cx=0.5, cy=0.22, zoom=1.0, face_h=0.2)
    _, y, _, _unused = crop_box(1920, 1080, tall)
    head_top = (tall.cy - tall.face_h * 1.05) * 1080
    assert y <= head_top  # the crop starts above the top of the head
