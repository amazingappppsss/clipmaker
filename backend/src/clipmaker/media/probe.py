"""FFprobe wrapper.

`probe_media` accepts a local path *or* an http(s) URL (e.g. a presigned storage URL);
ffprobe only reads the container header, so verifying a multi-GB upload is fast.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

PROBE_TIMEOUT_SECONDS = 60


class ProbeError(Exception):
    """The file could not be probed or is not a usable video."""


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Facts about a media file that the pipeline relies on."""

    duration_seconds: float
    width: int
    height: int
    fps: float
    video_codec: str
    has_audio: bool
    format_name: str
    raw: dict[str, Any]


def _parse_fps(rate: str | None) -> float:
    """Convert ffprobe's '30000/1001' style rates to float; 0.0 when unknown."""
    if not rate or rate in {"0/0", "N/A"}:
        return 0.0
    num, _, den = rate.partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _rotation(stream: dict[str, Any]) -> int:
    """Phone videos store rotation as side data; width/height must be swapped for ±90°."""
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            return int(side["rotation"])
    tag = (stream.get("tags") or {}).get("rotate")
    return int(tag) if tag else 0


def parse_probe_output(raw: dict[str, Any]) -> VideoMetadata:
    """Turn ffprobe JSON into VideoMetadata (pure function, unit-tested)."""
    streams = raw.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ProbeError("No video stream found")
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ProbeError("Video stream has no dimensions")
    if abs(_rotation(video)) % 180 == 90:
        width, height = height, width

    fmt = raw.get("format") or {}
    duration_str = fmt.get("duration") or video.get("duration")
    try:
        duration = float(duration_str)
    except (TypeError, ValueError) as exc:
        raise ProbeError("Unknown duration") from exc
    if duration <= 0:
        raise ProbeError("Video has zero duration")

    return VideoMetadata(
        duration_seconds=duration,
        width=width,
        height=height,
        fps=_parse_fps(video.get("avg_frame_rate")) or _parse_fps(video.get("r_frame_rate")),
        video_codec=str(video.get("codec_name") or "unknown"),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        format_name=str(fmt.get("format_name") or "unknown"),
        raw=raw,
    )


def probe_media(source: str) -> VideoMetadata:
    """Run ffprobe on a path or URL.

    Raises:
        ProbeError: if ffprobe fails, times out, or the file is not a usable video.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        source,
    ]
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd, capture_output=True, text=True, timeout=PROBE_TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("Timed out reading the video") from exc
    if result.returncode != 0:
        raise ProbeError(f"Not a readable video file: {result.stderr.strip()[:300]}")
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError("Unreadable probe output") from exc
    return parse_probe_output(raw)


#: A frame flatter than this has essentially no detail: a solid colour, not a picture.
BLANK_STDDEV = 2.5
#: Audio quieter than this over a whole clip is silence, whatever the track header says.
SILENT_DBFS = -60.0


def frame_variation(source: str, at_seconds: float) -> float | None:
    """How much the luma spreads across one frame, or None if it can't be measured.

    A solid white or black frame — what a mis-built filtergraph produces — spreads by zero.
    The file is a perfectly valid video, so nothing else in the quality check can see that it
    shows nothing.

    Measured as YMAX-YMIN rather than a standard deviation: not every ffmpeg build reports
    YSTD, and the spread is the plainer question anyway. `metadata=print` writes to a file
    handle rather than the log, so it is read from stdout instead of stderr.
    """
    try:
        argv = [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(0.0, at_seconds):.3f}",
            "-i",
            source,
            "-frames:v",
            "1",
            "-vf",
            "signalstats,metadata=print:file=-",
            "-f",
            "null",
            "-",
        ]
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    stats = result.stdout or ""
    low = re.search(r"signalstats\.YMIN=([0-9.]+)", stats)
    high = re.search(r"signalstats\.YMAX=([0-9.]+)", stats)
    if not low or not high:
        return None
    return float(high.group(1)) - float(low.group(1))


def mean_volume_dbfs(source: str) -> float | None:
    """Mean loudness of the whole file, or None if it can't be measured."""
    try:
        argv = ["ffmpeg", "-v", "error", "-i", source, "-af", "volumedetect", "-f", "null", "-"]
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv, capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", result.stderr or "")
    return float(match.group(1)) if match else None
