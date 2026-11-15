#!/usr/bin/env python
"""Render the landing page's hero demo with our own caption engine.

We have no footage we own, so the picture is synthetic: a warm, softly moving gradient behind
a vignette, at the vertical size we actually output. Everything over the top — the word-by-word
captions, the lime pop on the spoken word, the always-lit money words, the hook title card — is
produced by `clipmaker.editing.captions.build_ass`, the same code that captions real clips. So
the motion a visitor sees is genuinely our output, not a mock-up drawn in CSS.

Labelled as a demo wherever it appears. Run:  python scripts/make-demo-clip.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))

from clipmaker.editing.captions import build_ass  # noqa: E402
from clipmaker.providers.transcription.base import Word  # noqa: E402

OUT = ROOT / "frontend/public/demo"
FONT_DIR = ROOT / "backend/src/clipmaker/editing/fonts"

W, H, FPS = 540, 960, 24  # half our output size: identical look, a fraction of the bytes


def say(line: str, start: float, pace: float = 0.33) -> tuple[list[Word], float]:
    """Lay a sentence out as timed words, roughly at speaking pace."""
    words: list[Word] = []
    t = start
    for token in line.split():
        # Longer words take longer to say; it keeps the caption rhythm from feeling robotic.
        span = pace * (0.65 + min(len(token), 10) / 11)
        words.append(Word(text=token, start=round(t, 2), end=round(t + span * 0.92, 2)))
        t += span
    return words, t


SCRIPTS: list[dict] = [
    {
        "name": "quit-400k",
        "title": "He quit a $400K job",
        # Two tones so the background doesn't read as a flat colour swatch.
        "tone": ("0x2b1d4e", "0x7a3b55"),
        "lines": ["I walked away from $400K on a Tuesday.", "My mum didn't speak to me for a month."],
    },
    {
        "name": "never-checked",
        "title": "He never checked the account",
        "tone": ("0x13324b", "0x1e6f6b"),
        "lines": ["Wait. You NEVER checked the account?", "Not once in four years?"],
    },
]


def build(spec: dict) -> Path:
    words: list[Word] = []
    t = 0.45  # a beat before the first word, like a real cut
    for line in spec["lines"]:
        chunk, t = say(line, t)
        words.extend(chunk)
        t += 0.35  # breath between sentences
    duration = round(t + 0.6, 2)

    ass = build_ass(words, title=spec["title"], title_seconds=2.6)
    top, bottom = spec["tone"]
    out = OUT / f"{spec['name']}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "captions.ass").write_text(ass, encoding="utf-8")

        # The background is one still frame. An animated gradient changes every pixel of every
        # frame, which h264 cannot compress — the first cut of this was 3.4 MB for 8 seconds.
        # Rendering it once and letting the slow push-in supply the motion gives the same look
        # for a twentieth of the bytes.
        plate = work / "plate.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi",
                "-i", f"gradients=s={W}x{H}:c0={top}:c1={bottom}:x0={W // 2}:y0=0:"
                      f"x1={W}:y1={H}:d=1",
                "-frames:v", "1",
                "-vf", "gblur=sigma=22,vignette=PI/4.2",
                str(plate),
            ],
            check=True,
        )

        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-loop", "1", "-i", str(plate),
                "-t", str(duration),  # output length; `-t` before -i would cap the zoom instead
                "-vf",
                # d=1 means one output frame per input frame. With a larger `d`, zoompan expands
                # EVERY input frame into a whole pan — the first attempt produced 25 minutes of
                # video and a 2.6 MB file. `in` is the input frame number, so the push-in is a
                # function of time rather than of zoompan's internal counter.
                f"zoompan=z='min(1+0.0005*in,1.12)':d=1:x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
                f"format=yuv420p,ass=captions.ass:fontsdir={FONT_DIR}",
                "-an",  # the page autoplays it muted; audio would only add bytes
                "-c:v", "libx264", "-preset", "veryslow", "-crf", "32",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(out),
            ],
            check=True,
            cwd=work,
        )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in SCRIPTS:
        path = build(spec)
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
