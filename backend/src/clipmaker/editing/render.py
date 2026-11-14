"""FFmpeg render of one finished short: [teaser → rewind flash] → clip, 1080x1920 H.264.

Rendered in **segments**: each kept stretch is seeked, cropped to its 9:16 framing, scaled and
encoded on its own, then the parts are joined without re-encoding and captions are burned on in
a single final pass. That keeps memory flat (one piece in flight, not all of them) and lets a
clip from minute 90 of a 2-hour video render as fast as one from minute 1 — decoding the whole
source into one filter graph needs gigabytes of RAM and dies on small containers.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from clipmaker.core.resources import encoder_threads
from clipmaker.media.audio import MediaError

OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30
# Vertical sizes we render at. Full HD only when the source actually has that detail:
# blowing a 720p video up to 1080x1920 invents no detail and costs ~2.5x the encoding time.
SIZES = ((1080, 1920), (720, 1280))
FULL_HD_SOURCE_HEIGHT = 1080


def output_size(source_height: int) -> tuple[int, int]:
    """Render size for a source video this tall (pure, unit-tested)."""
    return SIZES[0] if source_height >= FULL_HD_SOURCE_HEIGHT else SIZES[1]


FLASH_SECONDS = 0.12  # a long white flash reads as a glitch; a quick blink reads as an edit
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
PART_CRF = 18  # intermediate quality; the visible loss after the final pass is negligible
# Threads are chosen from the container's real memory limit (core/resources.py): x264 buffers
# frames per thread, and a host that caps memory kills the process with no error at all.
RENDER_TIMEOUT_SECONDS = 1800

# Builds the ASS captions for one piece, given its [start, end) on the finished timeline.
CaptionsFor = Callable[[float, float], str]


@dataclass(frozen=True, slots=True)
class Piece:
    """One stretch of source video in the final edit."""

    start: float  # source seconds
    end: float
    crop: tuple[int, int, int, int]  # x, y, w, h in source pixels
    flash_out: bool = False  # last teaser piece: flash to white
    flash_in: bool = False  # first clip piece after the teaser: flash in from white

    @property
    def duration(self) -> float:
        return self.end - self.start


def piece_filter(piece: Piece, size: tuple[int, int] = (OUT_W, OUT_H)) -> str:
    """Video filter chain for one piece (pure, unit-tested)."""
    x, y, w, h = piece.crop
    out_w, out_h = size
    chain = (
        f"crop={w}:{h}:{x}:{y},scale={out_w}:{out_h}:flags=lanczos,"
        f"setsar=1,fps={OUT_FPS},format=yuv420p"
    )
    if piece.flash_out:
        st = max(0.0, round(piece.duration - FLASH_SECONDS, 3))
        chain += f",fade=t=out:st={st}:d={FLASH_SECONDS}:color=white"
    if piece.flash_in:
        chain += f",fade=t=in:st=0:d={FLASH_SECONDS + 0.05}:color=white"
    return chain


def loudness_filter() -> str:
    """Audio levelled to the -14 LUFS social platforms target (applied without touching video)."""
    return "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"


def _be_nice() -> None:
    """Run the encoder at low priority so the API keeps serving videos while it works."""
    with suppress(OSError):
        os.nice(10)


def _run(cmd: list[str], cwd: Path, what: str) -> None:
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            check=False,
            preexec_fn=_be_nice,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"{what} timed out") from exc
    if result.returncode != 0:
        raise MediaError(f"{what} failed: {result.stderr.strip()[-600:]}")


def render(
    source: str,
    pieces: list[Piece],
    out_path: Path,
    work_dir: Path,
    ass_text: str | None,
    *,
    preset: str = "veryfast",
    crf: int = 21,
    captions: CaptionsFor | None = None,
    size: tuple[int, int] | None = None,
) -> Path:
    """Render the edit to `out_path`. Raises MediaError on failure.

    The video is encoded exactly once: each piece is seeked, cropped, scaled and captioned in
    one pass, the parts are joined by copying, and only the audio is re-encoded for loudness.
    Re-encoding the joined video instead needs ~5x the memory and dies on small containers.
    """
    if not pieces:
        raise MediaError("Nothing to render")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_size = size or output_size(max(p.crop[3] for p in pieces))

    # 1) Each piece on its own: seek, crop, scale, burn its captions, encode.
    parts: list[Path] = []
    elapsed = 0.0
    for i, piece in enumerate(pieces):
        part = work_dir / f"part{i:03d}.mp4"
        chain = piece_filter(piece, out_size)
        if captions is not None:
            text = captions(elapsed, elapsed + piece.duration)
            if text.strip():
                name = f"captions{i:03d}.ass"
                (work_dir / name).write_text(text, encoding="utf-8")
                chain += f",ass={name}:fontsdir={FONTS_DIR}"
        elif ass_text and i == 0:  # legacy: whole-clip captions on the first piece only
            (work_dir / "captions.ass").write_text(ass_text, encoding="utf-8")
            chain += f",ass=captions.ass:fontsdir={FONTS_DIR}"
        _run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{piece.start:.3f}",
                "-t",
                f"{piece.duration:.3f}",
                "-i",
                source,
                "-vf",
                chain,
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-threads",
                str(encoder_threads()),
                "-x264-params",
                "sliced-threads=0:lookahead-threads=1",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-video_track_timescale",
                "90000",
                str(part),
            ],
            work_dir,
            f"Rendering part {i + 1}",
        )
        if not part.is_file() or part.stat().st_size == 0:
            raise MediaError(f"Part {i + 1} produced no output")
        parts.append(part)
        elapsed += piece.duration

    # 2) Join by copying (no video decode), then level the audio only.
    listing = work_dir / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = work_dir / "joined.mp4"
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            str(joined),
        ],
        work_dir,
        "Joining parts",
    )
    for part in parts:
        part.unlink(missing_ok=True)
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(joined),
            "-c:v",
            "copy",
            "-af",
            loudness_filter(),
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(out_path),
        ],
        work_dir,
        "Levelling audio",
    )
    joined.unlink(missing_ok=True)
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise MediaError("Rendering produced no output")
    return out_path
