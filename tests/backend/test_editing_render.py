"""editing/render.py — real FFmpeg render: teaser + flash + crops + captions → 1080x1920."""

from __future__ import annotations

from pathlib import Path

from clipmaker.editing.captions import build_ass
from clipmaker.editing.render import (
    OUT_H,
    OUT_W,
    Piece,
    build_filters,
    loudness_filter,
    output_size,
    render,
    split_runs,
)
from clipmaker.media.probe import probe_media
from clipmaker.providers.transcription.base import Word


def test_output_size_matches_the_source() -> None:
    assert output_size(1080) == (OUT_W, OUT_H)  # full-HD source keeps full-HD output
    assert output_size(2160) == (OUT_W, OUT_H)
    assert output_size(720) == (720, 1280)  # a 720p source is never blown up
    assert output_size(360) == (720, 1280)


def test_one_pass_keeps_only_the_wanted_stretches_and_moves_the_crop() -> None:
    teaser = Piece(8.0, 9.5, (100, 0, 404, 720), flash_out=True)
    main = Piece(2.0, 5.0, (300, 20, 404, 720), flash_in=True)
    video, audio = build_filters([teaser, main], offset=1.0, size=(720, 1280), ass_name="c.ass")

    # Dead air is dropped by selecting the stretches we keep, in source time after the seek.
    assert "between(t,7.000,8.500)" in video and "between(t,1.000,4.000)" in video
    assert "aselect=" in audio and "loudnorm=I=-14" in audio
    # One crop size for the whole clip; only its position moves, so this is a single pass.
    assert video.count("crop=") == 1 and "crop=404:720" in video
    assert "if(lt(t," in video and "100" in video and "300" in video
    assert "scale=720:1280" in video and "ass=c.ass" in video
    # Each flash is confined to its own instant, or it would white out the whole clip.
    assert video.count("fade=") == 2 and video.count("enable='between(t,") == 2


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


def test_captions_cover_the_whole_finished_clip(sample_video: Path, tmp_path: Path) -> None:
    """Captions are built once over the finished timeline and burned on in the same pass."""
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
    assert seen == [(0.0, 3.5)]  # one caption document for the whole 3.5 s edit


def test_flash_forward_hook_gets_its_own_run() -> None:
    """One pass can keep a stretch only once, in source order — the replayed hook needs two."""
    hook = Piece(30.0, 33.0, (0, 0, 2, 2), flash_out=True)  # a line from inside the clip
    body = [Piece(10.0, 20.0, (0, 0, 2, 2), flash_in=True), Piece(25.0, 40.0, (0, 0, 2, 2))]
    assert [len(r) for r in split_runs([hook, *body])] == [1, 2]
    assert len(split_runs(body)) == 1  # an ordinary clip stays a single pass
