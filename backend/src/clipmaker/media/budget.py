"""Will this video fit on the disk we have? — picking an import size before downloading.

A four-hour stream at 720p is 2.5-4 GB. The box this runs on has a 0.45 GB volume, so that
download cannot succeed at any resolution: it failed halfway through, mid-pipeline, after the
user had waited and been charged. A gaming VOD is exactly that shape, which makes this the
difference between "works for streamers" and "works for podcast episodes only".

So the size is decided up front, from the length of the video and the room we actually have,
and a video that cannot fit at the smallest size we are willing to clip from is refused
immediately with a reason.

Pure functions: the numbers are estimates and they are written down here so that changing one
is a decision somebody makes on purpose.
"""

from __future__ import annotations

#: Rough bytes per second of a downloaded H.264 stream with audio, by frame height. Measured
#: against YouTube and Twitch downloads and rounded up: a long VOD is often 60 fps, which is
#: the expensive case, and an estimate that is too low is the one that fills the disk.
BYTES_PER_SECOND: dict[int, float] = {
    1080: 800_000,
    720: 420_000,
    480: 190_000,
    360: 110_000,
}
#: Smallest height worth clipping from. Below this, captions and faces stop being legible in
#: a 1080x1920 render, so refusing is more honest than shipping a blurry clip.
MIN_USEFUL_HEIGHT = 360
#: Downloads run long and estimates are estimates; leave this much of the budget spare.
SAFETY = 0.8


def expected_bytes(duration_seconds: float, height: int) -> int:
    """How big we expect this download to be (pure)."""
    rate = BYTES_PER_SECOND.get(height)
    if rate is None:
        # An unlisted height: interpolate from the nearest known one, scaling by pixel area.
        nearest = min(BYTES_PER_SECOND, key=lambda h: abs(h - height))
        rate = BYTES_PER_SECOND[nearest] * (height / nearest) ** 2
    return int(max(0.0, duration_seconds) * rate)


def import_height(duration_seconds: float, budget: int | None, preferred: int) -> int | None:
    """The best height whose download fits the budget, or None if none does (pure).

    `budget` None means the room is not ours to know (object storage, not a local disk), so
    the preferred height stands.
    """
    if budget is None or duration_seconds <= 0:
        return preferred
    room = int(budget * SAFETY)
    for height in sorted((h for h in BYTES_PER_SECOND if h <= preferred), reverse=True):
        if expected_bytes(duration_seconds, height) <= room:
            return height
    return None


def longest_importable_seconds(budget: int | None) -> float | None:
    """How long a video we could take at the smallest useful height, or None for no limit."""
    if budget is None:
        return None
    return int(budget * SAFETY) / BYTES_PER_SECOND[MIN_USEFUL_HEIGHT]


def too_long_message(duration_seconds: float, budget: int | None) -> str:
    """What to tell someone whose video cannot be downloaded here (pure)."""
    limit = longest_importable_seconds(budget)
    theirs = (
        f"{duration_seconds / 3600:.1f} h"
        if duration_seconds >= 3600
        else (f"{duration_seconds / 60:.0f} min")
    )
    if limit is None:  # pragma: no cover - only reachable with no budget at all
        return f"This video ({theirs}) is too long to download here."
    return (
        f"This video is {theirs} long and we can only download about "
        f"{limit / 3600:.1f} h in one go right now. Upload the file instead, or import a "
        "shorter stretch of it."
    )
