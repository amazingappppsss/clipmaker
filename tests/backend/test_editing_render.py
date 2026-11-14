"""editing/render.py — real FFmpeg render: teaser + flash + crops + captions → 1080x1920."""

from __future__ import annotations

from pathlib import Path

from clipmaker.editing.captions import build_ass
from clipmaker.editing.render import OUT_H, OUT_W, Piece, final_filter, piece_filter, render
from clipmaker.media.probe import probe_media
from clipmaker.providers.transcription.base import Word


def test_piece_filter_crops_scales_and_flashes() -> None:
    teaser = Piece(8.0, 9.5, (100, 0, 404, 720), flash_out=True)
    assert "crop=404:720:100:0" in piece_filter(teaser)
    assert f"scale={OUT_W}:{OUT_H}" in piece_filter(teaser)
    assert "fade=t=out:st=1.3" in piece_filter(teaser) and "color=white" in piece_filter(teaser)
    assert "fade=t=in:st=0" in piece_filter(Piece(2.0, 5.0, (0, 0, 2, 2), flash_in=True))
    assert "fade=" not in piece_filter(Piece(2.0, 5.0, (0, 0, 2, 2)))


def test_final_pass_burns_captions_and_normalises_loudness() -> None:
    assert "ass=captions.ass" in final_filter("captions.ass")
    assert "loudnorm=I=-14" in final_filter(None) and "ass=" not in final_filter(None)


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
        build_ass(words, title="Test Clip"),
        preset="ultrafast",
    )
    meta = probe_media(str(out))
    assert (meta.width, meta.height) == (OUT_W, OUT_H)
    assert meta.has_audio
    assert abs(meta.duration_seconds - 5.5) < 0.4
