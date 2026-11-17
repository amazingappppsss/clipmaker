"""Deciding what we can download before we try — the four-hour-VOD problem.

A 4 h stream at 720p is 2.5-4 GB and the volume is 0.45 GB, so that download could not have
worked at any resolution. It failed halfway through, mid-pipeline, after the user had waited.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from clipmaker.media.budget import (
    BYTES_PER_SECOND,
    MIN_USEFUL_HEIGHT,
    expected_bytes,
    import_height,
    longest_importable_seconds,
    too_long_message,
)

GB = 1024**3
SMALL_VOLUME = int(0.27 * GB)  # what 0.45 GB leaves after headroom and the 60% share


def test_a_four_hour_stream_at_720p_is_measured_in_gigabytes() -> None:
    assert 2 * GB < expected_bytes(4 * 3600, 720) < 8 * GB


def test_a_short_video_keeps_the_resolution_we_prefer() -> None:
    assert import_height(5 * 60, SMALL_VOLUME, 720) == 720
    # Even on this disk, 10 minutes at 720p does not fit; it comes down a step instead.
    assert import_height(10 * 60, SMALL_VOLUME, 720) == 480


def test_a_longer_video_is_imported_smaller_rather_than_refused() -> None:
    """A half-hour episode must still work on a tiny disk, just at a lower resolution."""
    height = import_height(30 * 60, SMALL_VOLUME, 720)
    assert height is not None and height < 720
    assert expected_bytes(30 * 60, height) <= SMALL_VOLUME


def test_on_this_volume_even_an_hour_is_already_too_long() -> None:
    """Not a nice number: 0.27 GB of usable room is about 35 minutes at 360p.

    Which is the honest reason the box needs upgrading before a stream can be imported at
    all — and the reason this is refused in the API rather than halfway through a download.
    """
    assert import_height(60 * 60, SMALL_VOLUME, 720) is None
    assert import_height(60 * 60, 4 * GB, 720) == 720


def test_a_video_that_cannot_fit_at_the_smallest_useful_size_is_refused() -> None:
    assert import_height(4 * 3600, SMALL_VOLUME, 720) is None
    assert expected_bytes(4 * 3600, MIN_USEFUL_HEIGHT) > SMALL_VOLUME


def test_a_bigger_disk_takes_the_whole_thing() -> None:
    assert import_height(4 * 3600, 20 * GB, 720) == 720


def test_object_storage_has_no_local_limit_to_respect() -> None:
    assert import_height(4 * 3600, None, 720) == 720
    assert longest_importable_seconds(None) is None


def test_the_refusal_says_how_long_is_too_long_and_what_to_do_instead() -> None:
    message = too_long_message(4 * 3600, SMALL_VOLUME)
    assert "4.0 h" in message
    assert "Upload the file instead" in message
    limit = longest_importable_seconds(SMALL_VOLUME)
    assert limit is not None and f"{limit / 3600:.1f} h" in message


def test_an_unlisted_height_is_estimated_rather_than_ignored() -> None:
    assert 1440 not in BYTES_PER_SECOND
    assert expected_bytes(60, 1440) > expected_bytes(60, 1080)
    assert expected_bytes(0, 720) == 0
    assert expected_bytes(-10, 720) == 0


def test_a_stream_too_big_for_the_disk_is_refused_in_the_api(
    client: TestClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not halfway through the download, after the wait and the charge."""
    from clipmaker.api.deps import get_url_importer
    from clipmaker.main import app
    from clipmaker.media.url_import import RemoteVideo
    from clipmaker.services import imports

    class FourHourStream:
        def handles(self, url: str) -> bool:
            return True

        def inspect(self, url: str) -> RemoteVideo:
            return RemoteVideo(
                url=url,
                title="8 hour GTA grind",
                duration_seconds=3.9 * 3600,
                thumbnail_url=None,
                is_live=False,
            )

        def download(self, *a: object, **k: object) -> None:  # pragma: no cover - never reached
            raise AssertionError("the download must not be attempted")

    app.dependency_overrides[get_url_importer] = FourHourStream
    monkeypatch.setattr(imports, "budget_bytes", lambda _dir: SMALL_VOLUME)
    try:
        response = client.post(
            "/projects/import",
            json={"url": "https://www.twitch.tv/videos/123456789", "rights_confirmed": True},
            headers=auth,
        )
    finally:
        app.dependency_overrides.pop(get_url_importer, None)
    assert response.status_code == 422, response.text
    body = response.json()
    assert "Upload the file instead" in str(body)
