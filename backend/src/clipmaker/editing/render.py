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


def loudness_filter() -> str:
    """Audio levelled to the -14 LUFS social platforms target."""
    return "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"


def split_runs(pieces: list[Piece]) -> list[list[Piece]]:
    """Group pieces into runs that move forward through the source (pure, unit-tested).

    One FFmpeg pass can keep stretches of the source, but only once each and always in source
    order. The flash-forward hook replays a line from the middle of the clip, so it needs a run
    of its own; an ordinary clip is a single run and renders in one pass.
    """
    runs: list[list[Piece]] = []
    for piece in pieces:
        if runs and piece.start >= runs[-1][-1].end:
            runs[-1].append(piece)
        else:
            runs.append([piece])
    return runs


def _timeline(pieces: list[Piece]) -> list[tuple[float, float, Piece]]:
    """Each piece's span on the finished timeline (pure)."""
    out, at = [], 0.0
    for piece in pieces:
        out.append((at, at + piece.duration, piece))
        at += piece.duration
    return out


def _steps(values: list[tuple[float, int]]) -> str:
    """A piecewise FFmpeg expression over output time: value v until time t, then the next."""
    expr = str(values[-1][1])
    for until, value in reversed(values[:-1]):
        expr = f"if(lt(t,{until:.3f}),{value},{expr})"
    return expr


def build_filters(
    pieces: list[Piece], offset: float, size: tuple[int, int], ass_name: str | None
) -> tuple[str, str]:
    """The video and audio filter chains for one clip, in a single pass (pure, unit-tested).

    Everything happens in one decode: `select` keeps only the stretches we want (dead air
    dropped), the crop window *moves* over time to follow the speaker, captions are burned on
    and the audio is levelled. Cutting the clip into one FFmpeg run per shot instead costs a
    process start and a seek each time — the bulk of the old render time.
    """
    out_w, out_h = size
    spans = _timeline(pieces)
    keep = "+".join(f"between(t,{p.start - offset:.3f},{p.end - offset:.3f})" for _, _, p in spans)
    crop_w, crop_h = pieces[0].crop[2], pieces[0].crop[3]
    xs = [(end, p.crop[0]) for _, end, p in spans]
    ys = [(end, p.crop[1]) for _, end, p in spans]
    video = (
        f"select='{keep}',setpts=N/FRAME_RATE/TB,"
        f"crop={crop_w}:{crop_h}:x='{_steps(xs)}':y='{_steps(ys)}',"
        f"scale={out_w}:{out_h}:flags=lanczos,setsar=1,fps={OUT_FPS},format=yuv420p"
    )
    # `enable` confines each fade to its own instant: a fade placed mid-timeline without it
    # whites out every frame before (or after) it.
    for start, end, piece in spans:
        if piece.flash_out:
            at = max(0.0, end - FLASH_SECONDS)
            video += (
                f",fade=t=out:st={at:.3f}:d={FLASH_SECONDS}:color=white"
                f":enable='between(t,{at:.3f},{end:.3f})'"
            )
        if piece.flash_in:
            span = FLASH_SECONDS + 0.05
            video += (
                f",fade=t=in:st={start:.3f}:d={span:.3f}:color=white"
                f":enable='between(t,{start:.3f},{start + span:.3f})'"
            )
    if ass_name:
        video += f",ass={ass_name}:fontsdir={FONTS_DIR}"
    audio = f"aselect='{keep}',asetpts=N/SR/TB,{loudness_filter()}"
    return video, audio


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
    """Render the edit to `out_path` in a single FFmpeg pass. Raises MediaError on failure."""
    if not pieces:
        raise MediaError("Nothing to render")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_size = size or output_size(max(p.crop[3] for p in pieces))
    runs = split_runs(pieces)
    parts: list[Path] = []
    at = 0.0
    for i, run in enumerate(runs):
        offset = max(0.0, min(p.start for p in run) - 0.5)
        until = max(p.end for p in run) + 0.5
        span = sum(p.duration for p in run)
        name = f"run{i:02d}"
        ass_name = None
        text = (
            ass_text
            if (ass_text and len(runs) == 1)
            else (captions(at, at + span) if captions else None)
        )
        if text and text.strip():
            ass_name = f"{name}.ass"
            (work_dir / ass_name).write_text(text, encoding="utf-8")
        video, audio = build_filters(run, offset, out_size, ass_name)
        script = work_dir / f"{name}.txt"
        script.write_text(video, encoding="utf-8")
        part = out_path if len(runs) == 1 else work_dir / f"{name}.mp4"
        _run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{offset:.3f}",
                "-to",
                f"{until:.3f}",
                "-i",
                source,
                "-filter_script:v",
                str(script),
                "-af",
                audio,
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
                "-movflags",
                "+faststart",
                str(part),
            ],
            work_dir,
            f"Rendering {name}",
        )
        parts.append(part)
        at += span

    if len(parts) > 1:  # only the flash-forward hook needs joining
        listing = work_dir / "parts.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
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
                "-movflags",
                "+faststart",
                str(out_path),
            ],
            work_dir,
            "Joining the hook",
        )
        for part in parts:
            part.unlink(missing_ok=True)

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise MediaError("Rendering produced no output")
    return out_path
