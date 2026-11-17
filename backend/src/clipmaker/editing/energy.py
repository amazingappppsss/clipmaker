"""Finding moments by sound instead of by words.

Everything else in this pipeline reads a transcript. That works for a conversation and finds
nothing in gameplay: a crash, a clutch or a jumpscare has no quotable sentence, and our own
gates reject it for "needing outside context" even when it scores 9 for emotion.

This gives selection a second source. The loudest moments of a recording — a scream, a laugh,
gunfire, a crowd — are where something happened, whether or not anybody said anything about
it. Measured with ffmpeg alone: no model, no API, no per-minute cost.

Pure functions below the one call that reads the file, so the rules are testable without
rendering anything.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: How often loudness is sampled, as a count of audio frames. astats' `reset` counts frames,
#: not seconds — a 10 second file asked to reset every "0.5" returned 216 windows, not 20 —
#: so the real window length is derived from the recording's duration instead of assumed.
RESET_FRAMES = 20
#: Only used when the duration is unknown.
WINDOW_SECONDS = 0.5
#: A window this much louder than the recording's own median counts as a spike. Relative, so
#: it works on a quiet podcast and a loud stream without tuning.
SPIKE_OVER_MEDIAN_DB = 6.0
#: Spikes closer together than this are one moment, not several.
MERGE_WITHIN_SECONDS = 3.0
#: A moment shorter than this is a click or a gunshot, not something to clip.
MIN_MOMENT_SECONDS = 1.0
#: How much to keep either side of the spike: the wind-up, and the reaction after.
LEAD_SECONDS = 4.0
TAIL_SECONDS = 5.0

_LEVEL_LINE = re.compile(r"lavfi\.astats\.Overall\.RMS_level=(-?[0-9.]+|-inf)")


@dataclass(frozen=True, slots=True)
class Moment:
    """A stretch where the recording got loud, in source seconds."""

    start: float
    end: float
    peak_db: float
    #: How far above the recording's own median this peaked. Comparable across videos.
    above_median_db: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def median(values: list[float]) -> float:
    """Median of the values given (pure). Empty is treated as silence."""
    if not values:
        return -91.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def parse_levels(stdout: str) -> list[float]:
    """Per-window loudness in dBFS from ffmpeg's astats output (pure).

    Digital silence reports as -inf, which is not a number we can take a median of; it
    becomes the floor instead so a quiet stretch still counts as quiet rather than vanishing.
    """
    levels: list[float] = []
    for match in _LEVEL_LINE.finditer(stdout):
        raw = match.group(1)
        levels.append(-91.0 if raw == "-inf" else float(raw))
    return levels


def spikes(levels: list[float], window: float = WINDOW_SECONDS) -> list[Moment]:
    """Loud moments, relative to the recording's own median (pure).

    Relative rather than absolute: a podcast mastered quietly and a stream clipping into the
    red both have a median, and what matters is the jump away from it.
    """
    if not levels:
        return []
    floor = median(levels)
    found: list[Moment] = []
    for index, level in enumerate(levels):
        above = level - floor
        if above < SPIKE_OVER_MEDIAN_DB:
            continue
        at = index * window
        if found and at - found[-1].end <= MERGE_WITHIN_SECONDS:
            last = found[-1]
            found[-1] = Moment(
                start=last.start,
                end=at + window,
                peak_db=max(last.peak_db, level),
                above_median_db=max(last.above_median_db, above),
            )
        else:
            found.append(Moment(start=at, end=at + window, peak_db=level, above_median_db=above))
    return [m for m in found if m.duration >= MIN_MOMENT_SECONDS or m.above_median_db >= 12.0]


def widen(moment: Moment, duration: float) -> Moment:
    """Give a spike its wind-up and its reaction (pure).

    A crash is not the half second the metal hits. It is the few seconds of "oh no" before
    and the laughing afterwards — which is the part people actually clip.
    """
    return Moment(
        start=max(0.0, moment.start - LEAD_SECONDS),
        end=min(duration, moment.end + TAIL_SECONDS),
        peak_db=moment.peak_db,
        above_median_db=moment.above_median_db,
    )


def loud_moments(source: str, duration: float, limit: int = 40) -> list[Moment]:
    """The loudest moments of a recording, strongest first. [] when it can't be measured."""
    argv = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        source,
        "-af",
        f"astats=metadata=1:reset={RESET_FRAMES},ametadata=print:file=-",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv, capture_output=True, text=True, timeout=600, check=False
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("loudness_scan_failed")
        return []
    levels = parse_levels(result.stdout or "")
    # The true window: ffmpeg decided how many it would give us, and the file is as long as
    # it is. Deriving it keeps the timings right whatever frame size the codec uses.
    window = (duration / len(levels)) if levels and duration > 0 else WINDOW_SECONDS
    found = [widen(m, duration) for m in spikes(levels, window)]
    found.sort(key=lambda m: m.above_median_db, reverse=True)
    return found[:limit]
