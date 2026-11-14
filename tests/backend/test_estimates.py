"""services/estimates.py — the countdown shown while a video is being clipped."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from clipmaker.core.enums import ProjectState
from clipmaker.services.estimates import remaining_seconds, stage_estimate

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def _running(stage: ProjectState, seconds_ago: float) -> dict[str, dict[str, str]]:
    return {
        stage.value: {
            "status": "running",
            "started_at": (NOW - timedelta(seconds=seconds_ago)).isoformat(),
        }
    }


def test_counts_only_work_that_is_left() -> None:
    minutes, clips = 10.0, 5
    whole = remaining_seconds({}, minutes * 60, clips, NOW)
    assert whole is not None and whole > 0
    done = {
        s.value: {"status": "done"} for s in (ProjectState.INGESTING, ProjectState.TRANSCRIBING)
    }
    later = remaining_seconds(done, minutes * 60, clips, NOW)
    assert later is not None and later < whole


def test_elapsed_time_is_subtracted_but_never_hits_zero() -> None:
    estimate = stage_estimate(ProjectState.SELECTING, 10.0, 5)
    fresh = remaining_seconds(_running(ProjectState.SELECTING, 0), 600, 5, NOW)
    midway = remaining_seconds(_running(ProjectState.SELECTING, estimate / 2), 600, 5, NOW)
    overrun = remaining_seconds(_running(ProjectState.SELECTING, estimate * 5), 600, 5, NOW)
    assert fresh and midway and overrun
    assert midway < fresh
    assert overrun >= 10  # a slow stage keeps time on the clock instead of lying


def test_longer_videos_and_more_clips_take_longer() -> None:
    short = remaining_seconds({}, 300, 3, NOW)
    long = remaining_seconds({}, 3600, 3, NOW)
    many = remaining_seconds({}, 300, 12, NOW)
    assert short and long and many and short < long and short < many


def test_unknown_length_has_no_estimate() -> None:
    assert remaining_seconds({}, None, 5, NOW) is None
    assert remaining_seconds({}, 0, 5, NOW) is None
