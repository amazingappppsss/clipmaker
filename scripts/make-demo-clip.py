#!/usr/bin/env python
"""Render the landing page's hero demo from real footage.

Earlier versions painted a synthetic scene, which looked like what it was. This uses a real
podcast recording and puts it through the transformation the product actually performs: a wide
16:9 episode, unusable as a short, cropping to 9:16 on whoever is talking — and following the
floor when it changes hands.

**Footage**: Mixkit's free library (mixkit.co). The Mixkit Free License permits commercial use
with no attribution required; the file is not redistributed in the repository, only the small
rendered result. Someone else's podcast could not be used here at any quality: we would not own
it, and a takedown on the landing page is not a risk worth a nicer demo.

**The captions are illustrative, and the page says so.** The source has no audio track at all,
so there is no speech to contradict and nobody is being misquoted — these are licensed actors
in a staged scene, and the words demonstrate what our caption engine draws. They are timed to
the camera move, so the second line lands on whoever takes the floor: the reaction beat the
whole framework is built around.

Run:  python scripts/make-demo-clip.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/src"))

from clipmaker.editing.captions import build_ass  # noqa: E402
from clipmaker.providers.transcription.base import Word  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend/public/demo"
CACHE = ROOT / ".data/demo-source"
FONT_PATH = ROOT / "backend/src/clipmaker/editing/fonts/Montserrat-Black.ttf"

#: Mixkit free-licence podcast recording: two people, 16:9, one speaker change.
SOURCE_URL = "https://assets.mixkit.co/videos/2948/2948-720.mp4"
SOURCE_W, SOURCE_H = 1280, 720

W, H, FPS = 540, 960, 24  # half our output size: same look, a fraction of the bytes
LIME = (200, 255, 46)
INK = (11, 11, 18)

CROP_W = round(SOURCE_H * 9 / 16)  # the 9:16 window taken out of the wide frame
LEFT_X = 158  # the speaker on the left, centred
RIGHT_X = 818  # the speaker on the right

RAW_UNTIL, SNAP_UNTIL = 1.5, 2.1  # wide frame, then the crop closing in
TURN_AT, TURN_UNTIL = 4.7, 4.95  # the floor changes hands; the camera follows
DURATION = 7.0

#: Timed to the camera move: the first line belongs to the speaker on the left, the second to
#: whoever takes the floor at TURN_AT. The reaction is the payoff, so it lands on the cut.
LINES = [("I walked away from $400K on a Tuesday.", 2.2), ("Wait. You did WHAT?", 5.05)]
SOURCE_FROM = 1.2  # skip the first second, where nobody has started


def _ease(t: float, start: float, end: float) -> float:
    """0 before `start`, 1 after `end`, ease-out cubic between.

    A linear crop reads as a slider being dragged; this reads as an edit.
    """
    k = min(max((t - start) / (end - start), 0.0), 1.0)
    return 1 - (1 - k) ** 3


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _chip(
    draw: ImageDraw.ImageDraw,
    text: str,
    cx: float,
    y: float,
    size: int,
    bg: tuple[int, int, int],
    fg: tuple[int, int, int],
    radius: int = 8,
) -> None:
    font = _font(size)
    tw = draw.textlength(text, font=font)
    pad = size * 0.6
    draw.rounded_rectangle(
        [cx - tw / 2 - pad, y, cx + tw / 2 + pad, y + size * 1.7], radius=radius, fill=bg
    )
    draw.text((cx - tw / 2, y + size * 0.42), text, font=font, fill=fg)


def _layer(build: object) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    build(ImageDraw.Draw(img))  # type: ignore[operator]
    return img


def chrome() -> dict[str, Image.Image]:
    """The interface drawn over the footage, one transparent layer per phase."""

    def raw(d: ImageDraw.ImageDraw) -> None:
        # The letterboxed episode sits in the middle; label what is wrong with it.
        band_h = W * SOURCE_H / SOURCE_W
        top = (H - band_h) / 2
        _chip(d, "EPISODE · 1:42:08", W / 2, top - 52, 18, (0, 0, 0), (255, 255, 255), radius=16)
        _chip(
            d,
            "16:9 — WON'T FIT A PHONE",
            W / 2,
            top + band_h + 22,
            17,
            (0, 0, 0),
            (255, 255, 255),
            radius=16,
        )

    def snap(d: ImageDraw.ImageDraw) -> None:
        _chip(d, "RE-FRAMING ON THE SPEAKER", W / 2, H * 0.46, 19, LIME, INK, radius=19)

    def follow(d: ImageDraw.ImageDraw) -> None:
        _chip(d, "SPEAKER CHANGED — FOLLOWING", W / 2, H * 0.46, 19, LIME, INK, radius=19)

    def clip(d: ImageDraw.ImageDraw) -> None:
        _chip(d, "9:16 · READY TO POST", W / 2, 74, 20, LIME, INK)
        f = _font(19)
        d.ellipse([W - 70, 26, W - 26, 70], fill=(0, 0, 0))
        sw = d.textlength("94", font=f)
        d.text((W - 48 - sw / 2, 38), "94", font=f, fill=LIME)

    return {
        name: _layer(build)
        for name, build in (("raw", raw), ("snap", snap), ("follow", follow), ("clip", clip))
    }


def source() -> Path:
    """The footage, downloaded once and kept out of git."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / Path(SOURCE_URL).name
    if not path.exists():
        print(f"fetching {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, path)  # noqa: S310 - a fixed, known URL
    return path


def reframe(frame: Image.Image, t: float) -> Image.Image:
    """One output frame: the crop window at time `t`, fitted into the vertical canvas.

    ffmpeg's `crop` evaluates its width once and cannot animate, so the window is computed
    here instead. The result is the same geometry the renderer uses — a fixed-height 9:16
    window sliding across the source — just driven frame by frame.
    """
    snap = _ease(t, RAW_UNTIL, SNAP_UNTIL)
    turn = _ease(t, TURN_AT, TURN_UNTIL)

    width = SOURCE_W + (CROP_W - SOURCE_W) * snap
    left = (LEFT_X * snap) + (RIGHT_X - LEFT_X) * turn
    left = min(max(left, 0), SOURCE_W - width)

    window = frame.crop((round(left), 0, round(left + width), SOURCE_H))
    # Fit inside the vertical canvas, letterboxed while the window is still wide.
    ratio = min(W / window.width, H / window.height)
    size = (max(1, round(window.width * ratio)), max(1, round(window.height * ratio)))
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(window.resize(size, Image.LANCZOS), ((W - size[0]) // 2, (H - size[1]) // 2))
    return canvas


def decorate(canvas: Image.Image, t: float, art: dict[str, Image.Image]) -> Image.Image:
    """Our interface over the footage. No quotes: we don't know what they're saying."""
    out = canvas.convert("RGBA")
    if t < RAW_UNTIL:
        out = Image.alpha_composite(out, art["raw"])
        band = W * SOURCE_H / SOURCE_W
        top = (H - band) / 2
        scan = top + (band - 3) * ((t / RAW_UNTIL) % 1.0)
        line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(line).rectangle([0, scan, W, scan + 3], fill=(*LIME, 240))
        out = Image.alpha_composite(out, line)
    if RAW_UNTIL <= t < SNAP_UNTIL + 0.35:
        out = Image.alpha_composite(out, art["snap"])
    if TURN_AT <= t < TURN_UNTIL + 0.5:
        out = Image.alpha_composite(out, art["follow"])
    if t >= SNAP_UNTIL:
        out = Image.alpha_composite(out, art["clip"])

    bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    draw.rounded_rectangle([18, H - 27, W - 18, H - 21], radius=3, fill=(255, 255, 255, 210))
    draw.rounded_rectangle(
        [18, H - 27, 18 + (W - 36) * min(1.0, t / DURATION), H - 21], radius=3, fill=(*LIME, 255)
    )
    return Image.alpha_composite(out, bar).convert("RGB")


def captions() -> str:
    """Word timings for the two lines, captioned by the engine that captions real clips."""
    words: list[Word] = []
    for line, start in LINES:
        t = start
        for token in line.split():
            span = 0.3 * (0.65 + min(len(token), 10) / 11)
            words.append(Word(text=token, start=round(t, 2), end=round(t + span * 0.95, 2)))
            t += span
    return build_ass(words, title=None)  # the title card is part of the painted chrome


def build() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "podcast-reframe.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        # Decode the segment once, at source resolution, then do the work in Python.
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-ss", str(SOURCE_FROM), "-t", str(DURATION), "-i", str(source()),
                "-vf", f"fps={FPS},scale={SOURCE_W}:{SOURCE_H}",
                str(work / "src%04d.png"),
            ],
            check=True,
        )
        art = {name: img for name, img in chrome().items()}
        frames = sorted(work.glob("src*.png"))
        for i, path in enumerate(frames):
            with Image.open(path) as frame:
                decorate(reframe(frame.convert("RGB"), i / FPS), i / FPS, art).save(
                    work / f"out{i:04d}.png"
                )

        (work / "captions.ass").write_text(captions(), encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-framerate", str(FPS), "-i", "out%04d.png",
                "-vf", f"ass=captions.ass:fontsdir={FONT_PATH.parent}",
                "-an",  # the page autoplays it muted; audio would only add bytes
                "-c:v", "libx264", "-preset", "veryslow", "-crf", "31",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(out),
            ],
            check=True,
            cwd=work,
        )
    return out


def main() -> None:
    path = build()
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
