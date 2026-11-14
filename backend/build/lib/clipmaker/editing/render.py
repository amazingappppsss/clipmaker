"""FFmpeg render of one finished short: [teaser → rewind flash] → clip, 1080x1920 H.264.

Every piece is trimmed from the source, cropped to its 9:16 framing (following the speaker,
with punch-ins), scaled to 1080x1920 and concatenated; animated captions are burned in;
audio is loudness-normalised to the -14 LUFS that social platforms target. The source is
seeked to the clip's range first, so a clip from minute 90 of a 2-hour video renders as fast
as one from minute 1.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from clipmaker.media.audio import MediaError

OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30
FLASH_SECONDS = 0.2
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
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


def build_filtergraph(pieces: list[Piece], offset: float, ass_name: str | None) -> str:
    """The -filter_complex script (pure; unit-tested). `offset` = where the input was seeked."""
    lines = []
    for i, p in enumerate(pieces):
        s, e = round(p.start - offset, 3), round(p.end - offset, 3)
        x, y, w, h = p.crop
        v = (
            f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,crop={w}:{h}:{x}:{y},"
            f"scale={OUT_W}:{OUT_H}:flags=lanczos,setsar=1,fps={OUT_FPS}"
        )
        if p.flash_out:
            st = max(0.0, round(p.duration - FLASH_SECONDS, 3))
            v += f",fade=t=out:st={st}:d={FLASH_SECONDS}:color=white"
        if p.flash_in:
            v += f",fade=t=in:st=0:d={FLASH_SECONDS + 0.05}:color=white"
        lines.append(f"{v}[v{i}];")
        lines.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}];")
    inputs = "".join(f"[v{i}][a{i}]" for i in range(len(pieces)))
    lines.append(f"{inputs}concat=n={len(pieces)}:v=1:a=1[vc][ac];")
    if ass_name:
        lines.append(f"[vc]ass={ass_name}:fontsdir={FONTS_DIR}[vout];")
    else:
        lines.append("[vc]null[vout];")
    lines.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    return "\n".join(lines)


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
    offset = max(0.0, min(p.start for p in pieces) - 1.0)
    end = max(p.end for p in pieces) + 1.0
    ass_name = None
    if ass_text:
        ass_name = "captions.ass"
        (work_dir / ass_name).write_text(ass_text, encoding="utf-8")
    script = work_dir / "filters.txt"
    script.write_text(build_filtergraph(pieces, offset, ass_name), encoding="utf-8")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{offset:.3f}", "-to", f"{end:.3f}", "-i", source,
        "-filter_complex_script", str(script),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-r", str(OUT_FPS),
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart",
        str(out_path),
    ]  # fmt: skip
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaError("Rendering timed out") from exc
    if result.returncode != 0 or not out_path.is_file() or out_path.stat().st_size == 0:
        raise MediaError(result.stderr.strip()[-800:] or "Rendering failed")
    return out_path
