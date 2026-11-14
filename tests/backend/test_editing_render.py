"""editing/render.py — real FFmpeg render: teaser + flash + crops + captions → 1080x1920."""

from __future__ import annotations

from pathlib import Path

from clipmaker.editing.captions import build_ass
from clipmaker.editing.render import OUT_H, OUT_W, Piece, build_filtergraph, render
from clipmaker.media.probe import probe_media
from clipmaker.providers.transcription.base import Word


def test_filtergraph_has_flash_crops_and_loudness() -> None:
    pieces = [
        Piece(8.0, 9.5, (100, 0, 404, 720), flash_out=True),
        Piece(2.0, 5.0, (300, 0, 404, 720), flash_in=True),
    ]
    graph = build_filtergraph(pieces, offset=1.0, ass_name="captions.ass")
    assert "trim=start=7.0:end=8.5" in graph  # source times shifted by the seek offset
    assert "color=white" in graph and graph.count("fade=") == 2
    assert "concat=n=2" in graph and "loudnorm=I=-14" in graph and "ass=captions.ass" in graph


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
