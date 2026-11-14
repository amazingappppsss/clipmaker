"""editing/render.py — real FFmpeg render: teaser + flash + crops + captions → 1080x1920."""

from __future__ import annotations

from pathlib import Path

from clipmaker.editing.captions import build_ass
from clipmaker.editing.render import (
    OUT_H,
    OUT_W,
    Piece,
    loudness_filter,
    output_size,
    piece_filter,
    render,
)
from clipmaker.media.probe import probe_media
from clipmaker.providers.transcription.base import Word


def test_output_size_matches_the_source() -> None:
    assert output_size(1080) == (OUT_W, OUT_H)  # full-HD source keeps full-HD output
    assert output_size(2160) == (OUT_W, OUT_H)
    assert output_size(720) == (720, 1280)  # a 720p source is never blown up
    assert output_size(360) == (720, 1280)


def test_piece_filter_crops_scales_and_flashes() -> None:
    teaser = Piece(8.0, 9.5, (100, 0, 404, 720), flash_out=True)
    assert "crop=404:720:100:0" in piece_filter(teaser)
    assert f"scale={OUT_W}:{OUT_H}" in piece_filter(teaser)
    assert "fade=t=out:st=1.3" in piece_filter(teaser) and "color=white" in piece_filter(teaser)
    assert "fade=t=in:st=0" in piece_filter(Piece(2.0, 5.0, (0, 0, 2, 2), flash_in=True))
    assert "fade=" not in piece_filter(Piece(2.0, 5.0, (0, 0, 2, 2)))


def test_audio_is_levelled_for_social_platforms() -> None:
    assert "loudnorm=I=-14" in loudness_filter()


def test_renders_a_vertical_short(sample_video: Path, tmp_path: Path) -> None:
    pieces = [
        Piece(8.0, 9.5, (0, 0, 404, 720), flash_out=True),  # flash-forward teaser
        Piece(2.0, 4.0, (438, 0, 404, 720), flash_in=True),
        Piece(4.5, 6.5, (500, 60, 352, 626)),  # punch-in
    ]
    words = [Word("This", 0.2, 0.5), Word("is", 0.5, 0.7), Word("$28", 0.8, 1.3)]
    out = render(
        str(sample_video),
        pieces,
        tmp_path / "clip.mp4",
        tmp_path / "work",
        None,
        preset="ultrafast",
        captions=lambda a, b: build_ass(words, title="Test Clip", window=(a, b)),
    )
    meta = probe_media(str(out))
    # The 720p sample is never blown up to 1080x1920: that costs time and adds no detail.
    assert (meta.width, meta.height) == (720, 1280)
    assert meta.has_audio
    assert abs(meta.duration_seconds - 5.5) < 0.4


def test_captions_are_burned_into_each_piece(sample_video: Path, tmp_path: Path) -> None:
    """Captions are written per piece, so the joined video is never re-encoded."""
    seen: list[tuple[float, float]] = []

    def captions(start: float, end: float) -> str:
        seen.append((round(start, 2), round(end, 2)))
        return build_ass([Word("hi", start, start + 0.4)], window=(start, end))

    out = render(
        str(sample_video),
        [Piece(1.0, 3.0, (0, 0, 404, 720)), Piece(5.0, 6.5, (0, 0, 404, 720))],
        tmp_path / "c.mp4",
        tmp_path / "w",
        None,
        preset="ultrafast",
        captions=captions,
    )
    assert out.is_file()
    assert seen == [(0.0, 2.0), (2.0, 3.5)]  # windows follow the finished timeline
