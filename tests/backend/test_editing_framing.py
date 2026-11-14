"""editing/framing.py — speaker following, punch-ins, crop geometry."""

from __future__ import annotations

from clipmaker.editing.cuts import Interval
from clipmaker.editing.framing import (
    PUNCH_IN_ZOOM,
    Face,
    Sample,
    Shot,
    crop_box,
    plan_shots,
)


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


def test_frame_follows_whoever_is_talking() -> None:
    shots = plan_shots(_two_people(switch_at=4.0, until=8.0), [Interval(0, 8)])
    assert abs(shots[0].cx - 0.3) < 0.05
    assert abs(shots[-1].cx - 0.7) < 0.05


def test_long_shots_get_punch_ins() -> None:
    samples = [Sample(t / 4, [Face(0.5, 0.4, 0.1, motion=5)]) for t in range(0, 4 * 20)]
    shots = plan_shots(samples, [Interval(0, 20)])
    assert len(shots) >= 3
    assert {s.zoom for s in shots} == {1.0, PUNCH_IN_ZOOM}
    assert all(s.end - s.start <= 7 for s in shots)


def test_no_faces_means_steady_centre() -> None:
    shots = plan_shots([], [Interval(0, 4)])
    assert all(abs(s.cx - 0.5) < 1e-9 for s in shots)


def test_crop_is_9_16_and_inside_the_frame() -> None:
    x, y, w, h = crop_box(1920, 1080, Shot(0, 1, cx=0.98, cy=0.5))
    assert (w, h) == (606, 1080) and x + w <= 1920 and x >= 0
    x, y, w, h = crop_box(1920, 1080, Shot(0, 1, cx=0.5, cy=0.4, zoom=PUNCH_IN_ZOOM))
    assert h < 1080 and abs(w / h - 9 / 16) < 0.01 and y >= 0 and y + h <= 1080
    assert crop_box(1080, 1920, Shot(0, 1, 0.5, 0.5)) == (0, 0, 1080, 1920)  # already vertical
