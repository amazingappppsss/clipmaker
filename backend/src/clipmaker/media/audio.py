"""FFmpeg helpers for ingest: speech-optimised audio extraction and a preview thumbnail."""

from __future__ import annotations

import subprocess
from pathlib import Path

FFMPEG_TIMEOUT_SECONDS = 3600


class MediaError(Exception):
    """FFmpeg failed or produced no output."""


def _run(args: list[str], timeout: int = FFMPEG_TIMEOUT_SECONDS) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    except subprocess.TimeoutExpired as exc:
        raise MediaError("FFmpeg timed out") from exc
    if result.returncode != 0:
        raise MediaError(result.stderr.strip()[-500:] or "FFmpeg failed")


def extract_audio(source: str, dest: Path) -> Path:
    """Mono 16 kHz MP3 at 48 kbps (~21 MB/hour): ideal for speech recognition uploads."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "-i",
            source,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "48k",
            str(dest),
        ]
    )
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError("Audio extraction produced no output")
    return dest


def make_thumbnail(source: str, dest: Path, at_seconds: float, width: int = 640) -> Path:
    """Single JPEG frame, scaled to `width` (keeps aspect ratio)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "-ss",
            f"{max(at_seconds, 0):.2f}",
            "-i",
            source,
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-2",
            "-q:v",
            "4",
            str(dest),
        ],
        timeout=120,
    )
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError("Thumbnail extraction produced no output")
    return dest


def make_streamable(source: Path, dest: Path) -> Path:
    """Remux an MP4/MOV with its index at the front ("faststart") so browsers can play and seek
    without downloading the whole file. Stream copy only: no quality loss, takes seconds."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(["-i", str(source), "-map", "0", "-c", "copy", "-movflags", "+faststart", str(dest)])
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError("Remux produced no output")
    return dest
