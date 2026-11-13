"""FFprobe wrapper.

`probe_media` accepts a local path *or* an http(s) URL (e.g. a presigned storage URL);
ffprobe only reads the container header, so verifying a multi-GB upload is fast.
"""

from __future__ import annotations

import json
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
