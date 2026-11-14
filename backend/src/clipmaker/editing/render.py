"""FFmpeg render of one finished short: [teaser → rewind flash] → clip, 1080x1920 H.264.

Rendered in **segments**: each kept stretch is seeked, cropped to its 9:16 framing, scaled and
encoded on its own, then the parts are joined without re-encoding and captions are burned on in
a single final pass. That keeps memory flat (one piece in flight, not all of them) and lets a
clip from minute 90 of a 2-hour video render as fast as one from minute 1 — decoding the whole
source into one filter graph needs gigabytes of RAM and dies on small containers.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from clipmaker.media.audio import MediaError

OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30
FLASH_SECONDS = 0.2
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
PART_CRF = 18  # intermediate quality; the visible loss after the final pass is negligible
# x264 buffers frames per thread; 1080x1920 with many threads needs ~600 MB+, which small
# containers kill. Two threads keep a render near 300 MB and are plenty for short clips.
ENCODE_THREADS = "2"
RENDER_TIMEOUT_SECONDS = 1800


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


def piece_filter(piece: Piece) -> str:
    """Video filter chain for one piece (pure, unit-tested)."""
    x, y, w, h = piece.crop
    chain = (
        f"crop={w}:{h}:{x}:{y},scale={OUT_W}:{OUT_H}:flags=lanczos,"
        f"setsar=1,fps={OUT_FPS},format=yuv420p"
    )
    if piece.flash_out:
        st = max(0.0, round(piece.duration - FLASH_SECONDS, 3))
        chain += f",fade=t=out:st={st}:d={FLASH_SECONDS}:color=white"
    if piece.flash_in:
        chain += f",fade=t=in:st=0:d={FLASH_SECONDS + 0.05}:color=white"
    return chain


def final_filter(ass_name: str | None) -> str:
    """Filters for the joining pass: burned-in captions and broadcast-level loudness."""
    video = f"ass={ass_name}:fontsdir={FONTS_DIR}" if ass_name else "null"
    return f"-vf|{video}|-af|loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"


def _run(cmd: list[str], cwd: Path, what: str) -> None:
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            check=False,
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
) -> Path:
    """Render the edit to `out_path`. Raises MediaError on failure."""
    if not pieces:
        raise MediaError("Nothing to render")
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1) Each piece on its own: seek, crop, scale, encode. Memory stays flat.
    parts: list[Path] = []
    for i, piece in enumerate(pieces):
        part = work_dir / f"part{i:03d}.mp4"
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
                piece_filter(piece),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                str(PART_CRF),
                "-threads",
                ENCODE_THREADS,
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

    # 2) Join without re-encoding, then one pass for captions and loudness.
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

    ass_name = None
    if ass_text:
        ass_name = "captions.ass"
        (work_dir / ass_name).write_text(ass_text, encoding="utf-8")
    video_filter, audio_filter = final_filter(ass_name).split("|-af|")
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(joined),
            *video_filter.split("|"),
            "-af",
            audio_filter,
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-threads",
            ENCODE_THREADS,
            "-x264-params",
            "sliced-threads=0:lookahead-threads=1",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-r",
            str(OUT_FPS),
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(out_path),
        ],
        work_dir,
        "Finishing the clip",
    )
    joined.unlink(missing_ok=True)
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise MediaError("Rendering produced no output")
    return out_path
