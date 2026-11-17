"""Finding moments by sound, for content where nobody says anything quotable."""

from __future__ import annotations

import subprocess
from pathlib import Path

from clipmaker.editing.energy import (
    LEAD_SECONDS,
    MERGE_WITHIN_SECONDS,
    SPIKE_OVER_MEDIAN_DB,
    TAIL_SECONDS,
    Moment,
    loud_moments,
    median,
    parse_levels,
    spikes,
    widen,
)


def _levels(pattern: list[float]) -> list[float]:
    return pattern


def test_quiet_recording_has_no_spikes() -> None:
    assert spikes([-30.0] * 20) == []


def test_a_shout_is_found_and_measured_against_the_recordings_own_median() -> None:
    """A quiet podcast and a loud stream both have a median; the jump is what matters."""
    quiet = [-40.0] * 10 + [-40.0 + SPIKE_OVER_MEDIAN_DB + 2] * 4 + [-40.0] * 10
    loud = [-12.0] * 10 + [-12.0 + SPIKE_OVER_MEDIAN_DB + 2] * 4 + [-12.0] * 10

    for levels in (quiet, loud):
        found = spikes(levels)
        assert len(found) == 1, levels[:3]
        assert found[0].above_median_db >= SPIKE_OVER_MEDIAN_DB
        assert found[0].start == 10 * 0.5


def test_spikes_close_together_are_one_moment() -> None:
    """A burst of gunfire is one clip, not nine."""
    levels = [-30.0] * 6
    for _ in range(4):
        levels += [-18.0, -30.0]  # a spike every second
    levels += [-30.0] * 6
    found = spikes(levels)
    assert len(found) == 1, f"{len(found)} moments for one burst"
    assert found[0].duration <= MERGE_WITHIN_SECONDS + 4


def test_a_single_blip_is_not_a_moment_unless_it_is_enormous() -> None:
    small = [-30.0] * 10 + [-30.0 + SPIKE_OVER_MEDIAN_DB + 1] + [-30.0] * 10
    assert spikes(small) == []
    huge = [-30.0] * 10 + [-30.0 + 20] + [-30.0] * 10
    assert len(spikes(huge)) == 1, "a scream well above everything is worth keeping"


def test_a_moment_keeps_its_wind_up_and_its_reaction() -> None:
    """A crash is not the half second of impact: it is the "oh no" and the laughing after."""
    wide = widen(Moment(start=30.0, end=31.0, peak_db=-10.0, above_median_db=9.0), 120.0)
    assert wide.start == 30.0 - LEAD_SECONDS
    assert wide.end == 31.0 + TAIL_SECONDS

    # Never past the ends of the recording.
    clamped = widen(Moment(start=1.0, end=2.0, peak_db=-10.0, above_median_db=9.0), 4.0)
    assert clamped.start == 0.0
    assert clamped.end == 4.0


def test_digital_silence_is_a_floor_not_a_hole() -> None:
    """ffmpeg reports true silence as -inf, which has no median."""
    levels = parse_levels(
        "lavfi.astats.Overall.RMS_level=-inf\nlavfi.astats.Overall.RMS_level=-22.5\n"
    )
    assert levels == [-91.0, -22.5]
    assert median([]) == -91.0
    assert median([-10.0, -20.0]) == -15.0
    assert median([-10.0, -20.0, -30.0]) == -20.0


def test_it_finds_a_real_shout_in_a_real_file(tmp_path: Path) -> None:
    """End to end against ffmpeg, because parsing its output is half the risk."""
    quiet = tmp_path / "quiet.wav"
    shout = tmp_path / "shout.wav"
    whole = tmp_path / "whole.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=200:duration=4:sample_rate=44100",
            "-af",
            "volume=-30dB",
            str(quiet),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=800:duration=2:sample_rate=44100",
            str(shout),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(quiet),
            "-i",
            str(shout),
            "-i",
            str(quiet),
            "-filter_complex",
            "[0:a][1:a][2:a]concat=n=3:v=0:a=1",
            str(whole),
        ],
        check=True,
    )

    found = loud_moments(str(whole), duration=10.0)
    assert found, "the shout was not found"
    loudest = found[0]
    # The shout sits between 4s and 6s; the widened moment must contain it.
    assert loudest.start <= 4.5 and loudest.end >= 5.5, (loudest.start, loudest.end)


def test_an_unreadable_file_yields_nothing_rather_than_raising() -> None:
    """Selection must carry on with speech alone if the audio cannot be measured."""
    assert loud_moments("/nonexistent/path.mp4", duration=10.0) == []
