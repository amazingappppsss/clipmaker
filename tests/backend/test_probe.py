"""media/probe.py — parsing rules and a real ffprobe run."""

from __future__ import annotations

from pathlib import Path

import pytest

from clipmaker.media.probe import ProbeError, parse_probe_output, probe_media


def _raw(**video: object) -> dict[str, object]:
    stream = {
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1920,
        "height": 1080,
        "avg_frame_rate": "30000/1001",
        **video,
    }
    return {
        "streams": [stream, {"codec_type": "audio"}],
        "format": {"duration": "61.5", "format_name": "mov,mp4"},
    }


def test_parses_basic_metadata() -> None:
    meta = parse_probe_output(_raw())
    assert (meta.width, meta.height) == (1920, 1080)
    assert meta.duration_seconds == pytest.approx(61.5)
    assert meta.fps == pytest.approx(29.97, rel=1e-3)
    assert meta.has_audio is True


def test_rotation_swaps_dimensions() -> None:
    meta = parse_probe_output(_raw(side_data_list=[{"rotation": -90}]))
    assert (meta.width, meta.height) == (1080, 1920)


def test_rejects_audio_only_files() -> None:
    with pytest.raises(ProbeError, match="No video stream"):
        parse_probe_output({"streams": [{"codec_type": "audio"}], "format": {"duration": "5"}})


def test_rejects_unknown_duration() -> None:
    raw = _raw()
    raw["format"] = {}
    with pytest.raises(ProbeError, match="duration"):
        parse_probe_output(raw)


def test_probe_real_file(sample_video: Path) -> None:
    meta = probe_media(str(sample_video))
    assert (meta.width, meta.height) == (1280, 720)
    assert meta.duration_seconds == pytest.approx(12, abs=0.2)
    assert meta.has_audio


def test_probe_garbage_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"definitely not a video" * 100)
    with pytest.raises(ProbeError):
        probe_media(str(bad))


def test_make_streamable_moves_index_to_front(sample_video: Path, tmp_path: Path) -> None:
    from clipmaker.media.audio import make_streamable

    out = make_streamable(sample_video, tmp_path / "s.mp4")
    head = out.read_bytes()[:4096]
    assert head.find(b"moov") != -1 and (
        head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat")
    )
    assert probe_media(str(out)).has_audio


def test_a_blank_render_is_caught_even_though_the_file_is_valid(tmp_path: Path) -> None:
    """A misplaced fade once whited out every frame and every other check passed it."""
    import subprocess

    from clipmaker.media.probe import BLANK_STDDEV, frame_variation

    flat = tmp_path / "white.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=320x568:d=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(flat),
        ],
        check=True,
    )
    busy = tmp_path / "busy.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=s=320x568:d=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(busy),
        ],
        check=True,
    )

    blank = frame_variation(str(flat), 1.0)
    detailed = frame_variation(str(busy), 1.0)
    assert blank is not None and detailed is not None, "measurement is unavailable"
    assert blank < BLANK_STDDEV
    assert detailed > BLANK_STDDEV


def test_looks_blank_says_nothing_when_nothing_could_be_measured() -> None:
    """A missing tool must not fail a clip that is probably fine."""
    from clipmaker.pipeline.stages.qa import looks_blank

    assert looks_blank([None, None]) is False
    assert looks_blank([0.1, 0.2]) is True
    assert looks_blank([0.1, 40.0]) is False, "one real frame is enough to pass"
