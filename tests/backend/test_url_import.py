"""Link import (YouTube): URL safety, error mapping, API rules and the worker download path."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clipmaker.media.url_import import RemoteVideo, UrlImportError, _classify, validate_url


# --- URL allow-list ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "youtu.be/abc123",
        "https://youtube.com/shorts/x",
        "  https://m.youtube.com/watch?v=abc  ",
    ],
)
def test_youtube_urls_accepted(url: str) -> None:
    assert validate_url(url).startswith("https://")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.twitch.tv/videos/123456789",
        "https://twitch.tv/somestreamer/clip/FunnyCrashHere",
        "clips.twitch.tv/FunnyCrashHere",
        "https://m.twitch.tv/videos/123456789",
    ],
)
def test_twitch_vods_and_clips_accepted(url: str) -> None:
    """Gaming clippers work on Twitch. Refusing their links made the audience unreachable."""
    assert validate_url(url).startswith("https://")


@pytest.mark.parametrize(
    "url",
    ["https://twitch.tv.evil.com/x", "http://twitch.tv/videos/1", "https://notwitch.tv/videos/1"],
)
def test_twitch_lookalikes_rejected(url: str) -> None:
    with pytest.raises(UrlImportError) as err:
        validate_url(url)
    assert err.value.code == "unsupported_url"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/watch?v=abc",
        "https://evil.com/watch?v=youtube.com",
        "https://youtube.com.evil.com/x",
        "https://user:pw@youtube.com/x",
        "https://youtube.com:8443/x",
        "file:///etc/passwd",
        "https://169.254.169.254/latest",
    ],
)
def test_unsafe_or_foreign_urls_rejected(url: str) -> None:
    with pytest.raises(UrlImportError) as err:
        validate_url(url)
    assert err.value.code == "unsupported_url"


@pytest.mark.parametrize(
    ("message", "code", "retryable"),
    [
        ("ERROR: Sign in to confirm you're not a bot", "source_blocked", True),
        ("ERROR: Private video", "source_private", False),
        ("ERROR: Video unavailable", "source_unavailable", False),
        ("ERROR: Connection timed out", "source_network", True),
        ("ERROR: something odd", "source_failed", False),
    ],
)
def test_error_classification(message: str, code: str, retryable: bool) -> None:
    err = _classify(message)
    assert (err.code, err.retryable) == (code, retryable)


# --- fake importer ----------------------------------------------------------------------
class FakeImporter:
    def __init__(
        self, video: Path, duration: float = 12.0, fail: UrlImportError | None = None
    ) -> None:
        self.video, self.duration, self.fail = video, duration, fail
        self.downloads = 0

    def handles(self, url: str) -> bool:
        return True

    def inspect(self, url: str) -> RemoteVideo:
        if self.fail and self.fail.code != "source_blocked":
            raise self.fail
        return RemoteVideo(
            url=url,
            title="My Podcast Ep 1",
            duration_seconds=self.duration,
            thumbnail_url=None,
            is_live=False,
        )

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        self.downloads += 1
        heartbeat()
        if self.fail:
            raise self.fail
        dest_dir.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy(self.video, dest_dir / "source.mp4"))


@pytest.fixture
def importer(client: TestClient, sample_video: Path) -> Iterator[FakeImporter]:
    from clipmaker.api.deps import get_url_importer
    from clipmaker.main import app

    fake = FakeImporter(sample_video)
    app.dependency_overrides[get_url_importer] = lambda: fake
    yield fake


def _import(client: TestClient, auth: dict[str, str], **body: object) -> dict:
    payload = {"url": "https://youtu.be/abc123", "rights_confirmed": True, **body}
    return client.post("/projects/import", json=payload, headers=auth).json()


# --- API ----------------------------------------------------------------------------------
def test_import_creates_ready_project(
    client: TestClient, auth: dict[str, str], importer: FakeImporter
) -> None:
    project = _import(client, auth)
    assert project["title"] == "My Podcast Ep 1"
    assert project["state"] == "UPLOADED"
    assert project["source_video"]["source_kind"] == "url"
    assert project["source_video"]["duration_seconds"] == 12.0
    assert importer.downloads == 0  # nothing downloaded inside the API request


def test_import_requires_rights_confirmation(
    client: TestClient, auth: dict[str, str], importer: FakeImporter
) -> None:
    assert _import(client, auth, rights_confirmed=False)["code"] == "rights_not_confirmed"


def test_import_rejects_bad_links_and_lengths(
    client: TestClient, auth: dict[str, str], importer: FakeImporter
) -> None:
    assert _import(client, auth, url="https://vimeo.com/123")["code"] == "unsupported_url"
    importer.duration = 5 * 3600
    assert _import(client, auth)["code"] == "too_long"
    importer.duration, importer.fail = (
        60,
        UrlImportError("source_private", "This video is private."),
    )
    assert _import(client, auth)["code"] == "source_private"


def test_kill_switch(
    client: TestClient,
    auth: dict[str, str],
    importer: FakeImporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clipmaker.core.config import get_settings

    monkeypatch.setattr(get_settings(), "enable_url_import", False)
    res = client.post(
        "/projects/import",
        headers=auth,
        json={"url": "https://youtu.be/x", "rights_confirmed": True},
    )
    assert res.status_code == 403 and res.json()["code"] == "url_import_disabled"


# --- worker download path -----------------------------------------------------------------
def _run(job_id: uuid.UUID, importer: FakeImporter) -> object:
    from clipmaker.core.config import get_settings
    from clipmaker.db.session import get_session_factory
    from clipmaker.pipeline.runner import JobRunner
    from clipmaker.storage.factory import get_storage
    from pipeline_fakes import FakeLLM, FakeTranscriber, analysis_only_handlers

    runner = JobRunner(
        job_id,
        "w",
        get_settings(),
        get_storage(),
        get_session_factory(),
        handlers=analysis_only_handlers(),
        llm_factory=lambda s: FakeLLM(),
        transcriber_factory=lambda s: FakeTranscriber(),
        importer_factory=lambda s: importer,
    )
    return runner.run()[0]


def test_imported_video_is_downloaded_verified_and_clipped(
    client: TestClient, auth: dict[str, str], importer: FakeImporter, queued: list[uuid.UUID]
) -> None:
    from clipmaker.pipeline.runner import Outcome

    pid = _import(client, auth)["id"]
    assert client.post(f"/projects/{pid}/process", headers=auth).status_code == 202
    assert _run(queued[-1], importer) == Outcome.PAUSED
    project = client.get(f"/projects/{pid}", headers=auth).json()
    src = project["source_video"]
    assert src["upload_status"] == "verified" and src["width"] == 1280 and src["size_bytes"] > 0
    assert project["source_video_url"] and project["thumbnail_url"]
    assert len(client.get(f"/projects/{pid}/clips", headers=auth).json()) >= 1
    # Re-running does not download again.
    from clipmaker.db.models import ProcessingJob
    from clipmaker.db.session import get_session_factory

    with get_session_factory()() as db:
        job = db.get(ProcessingJob, queued[-1])
        assert job is not None
        job.stages = {}
        db.commit()
    _run(queued[-1], importer)
    assert importer.downloads == 1


def test_blocked_download_fails_with_clear_message_and_refund(
    client: TestClient, auth: dict[str, str], importer: FakeImporter, queued: list[uuid.UUID]
) -> None:
    from clipmaker.pipeline.runner import Outcome

    pid = _import(client, auth)["id"]
    client.post(f"/projects/{pid}/process", headers=auth)
    importer.fail = _classify("Sign in to confirm you're not a bot")
    outcomes = [_run(queued[-1], importer) for _ in range(3)]
    assert outcomes == [Outcome.RETRY, Outcome.RETRY, Outcome.FAILED]
    project = client.get(f"/projects/{pid}", headers=auth).json()
    assert "upload the file instead" in project["error_message"]
    assert "refunded" in project["error_message"]


# --- Apify managed downloader -------------------------------------------------------------
import json as _json  # noqa: E402

import httpx  # noqa: E402

from clipmaker.media.url_import import (  # noqa: E402
    ApifyImporter,
    FallbackImporter,
    YtDlpImporter,
    build_url_importer,
)

YT = "https://www.youtube.com/watch?v=abc123"
TWITCH = "https://www.twitch.tv/videos/123456789"


def _apify(
    items: object, status: int = 200, file_status: int = 200, seen: dict[str, object] | None = None
) -> ApifyImporter:
    seen = seen if seen is not None else {}

    def api(req: httpx.Request) -> httpx.Response:
        seen["api_auth"] = req.headers.get("authorization")
        seen["api_path"] = req.url.path
        seen["api_body"] = _json.loads(req.content)
        return httpx.Response(status, json=items)

    def files(req: httpx.Request) -> httpx.Response:
        seen["file_auth"] = req.headers.get("authorization")
        return httpx.Response(file_status, content=b"\x00\x00\x00\x18ftypmp42" + b"x" * 5000)

    return ApifyImporter(
        "apify-test-token",
        "coder2077~youtube-video-downloader",
        "1080p",
        client=httpx.Client(
            base_url="https://api.apify.test",
            transport=httpx.MockTransport(api),
            headers={"Authorization": "Bearer apify-test-token"},
        ),
        download_client=httpx.Client(transport=httpx.MockTransport(files)),
    )


OK_ITEM = {
    "ok": True,
    "url": YT,
    "duration": 577,
    "filename": "My Great Podcast Ep 4 (1080p, av1, youtube).mp4",
    "download_url": "https://api.fastsaver.test/v1/tunnel?id=x",
    "thumbnails": {"max": "https://i.ytimg.com/x.jpg"},
}


def test_apify_inspect_parses_title_and_duration() -> None:
    seen: dict[str, object] = {}
    info = _apify([OK_ITEM], seen=seen).inspect(YT)
    assert info.title == "My Great Podcast Ep 4"
    assert info.duration_seconds == 577
    assert (
        seen["api_path"] == "/v2/acts/coder2077~youtube-video-downloader/run-sync-get-dataset-items"
    )
    assert seen["api_body"] == {"urls": [YT], "format": "1080p"}
    assert seen["api_auth"] == "Bearer apify-test-token"


def test_apify_download_streams_file_without_leaking_token(tmp_path: Path) -> None:
    seen: dict[str, object] = {}
    beats: list[int] = []
    path = _apify([OK_ITEM], seen=seen).download(YT, tmp_path / "dl", lambda: beats.append(1))
    assert path.name == "source.mp4" and path.stat().st_size > 5000
    assert seen["file_auth"] is None  # the Apify token never goes to the file host


@pytest.mark.parametrize(
    ("items", "status", "code", "retryable"),
    [
        ([{"ok": False, "error": "Video unavailable"}], 200, "source_unavailable", False),
        ([{"ok": False, "error": "This is a private video"}], 200, "source_private", False),
        ([], 200, "source_failed", True),
        ([OK_ITEM], 401, "importer_unavailable", False),
        ([OK_ITEM], 402, "importer_unavailable", False),
        ([OK_ITEM], 503, "source_network", True),
    ],
)
def test_apify_errors(items: object, status: int, code: str, retryable: bool) -> None:
    with pytest.raises(UrlImportError) as err:
        _apify(items, status=status).inspect(YT)
    assert (err.value.code, err.value.retryable) == (code, retryable)


def test_apify_expired_link_is_retryable(tmp_path: Path) -> None:
    with pytest.raises(UrlImportError) as err:
        _apify([OK_ITEM], file_status=410).download(YT, tmp_path, lambda: None)
    assert err.value.retryable


class _Stub:
    def __init__(self, error: UrlImportError | None, title: str, *, takes: bool = True) -> None:
        self.error, self.title, self.calls = error, title, 0
        self._takes = takes

    def handles(self, url: str) -> bool:
        return self._takes

    def inspect(self, url: str) -> RemoteVideo:
        self.calls += 1
        if self.error:
            raise self.error
        return RemoteVideo(
            url=url, title=self.title, duration_seconds=60, thumbnail_url=None, is_live=False
        )

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        raise NotImplementedError


def test_fallback_moves_on_when_blocked_or_broken() -> None:
    blocked = _Stub(_classify("Sign in to confirm you're not a bot"), "a")
    broken = _Stub(UrlImportError("importer_unavailable", "bad key"), "b")
    good = _Stub(None, "from-third")
    assert FallbackImporter([blocked, broken, good]).inspect(YT).title == "from-third"


def test_fallback_stops_on_video_problems() -> None:
    private = _Stub(_classify("Private video"), "a")
    never = _Stub(None, "b")
    with pytest.raises(UrlImportError, match="private"):
        FallbackImporter([private, never]).inspect(YT)
    assert never.calls == 0


def test_an_importer_that_cannot_take_the_link_is_not_even_tried() -> None:
    """Apify's actor is YouTube-only: handing it a Twitch VOD burns a paid run to fail."""
    wrong_provider = _Stub(None, "apify", takes=False)
    right = _Stub(None, "ytdlp")
    assert FallbackImporter([wrong_provider, right]).inspect(TWITCH).title == "ytdlp"
    assert wrong_provider.calls == 0


def test_a_link_no_provider_can_take_says_so_rather_than_failing_a_download() -> None:
    only = _Stub(None, "apify", takes=False)
    chain = FallbackImporter([only])
    assert chain.handles(TWITCH) is False
    with pytest.raises(UrlImportError) as err:
        chain.inspect(TWITCH)
    assert err.value.code == "unsupported_url"
    assert only.calls == 0


def test_apify_skips_twitch_and_takes_youtube() -> None:
    importer = ApifyImporter("tok", "coder2077~youtube-video-downloader")
    assert importer.handles(TWITCH) is False
    assert importer.handles(YT) is True
    assert YtDlpImporter().handles(TWITCH) is True


def test_build_chain_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import SecretStr

    from clipmaker.core.config import get_settings

    s = get_settings()
    assert isinstance(build_url_importer(s), YtDlpImporter)  # no APIFY_TOKEN → yt-dlp only
    monkeypatch.setattr(s, "apify_token", SecretStr("tok"))
    assert isinstance(build_url_importer(s), FallbackImporter)
    # yt-dlp is the only provider that speaks Twitch, so it stays in the chain even when
    # only Apify is configured — otherwise every VOD would be refused.
    monkeypatch.setattr(s, "url_import_providers", "apify")
    chain = build_url_importer(s)
    assert isinstance(chain, FallbackImporter)
    assert chain.handles(TWITCH) is True


# --- unknown length (download services that report duration: null) ---------------------------
def _credits(client: TestClient, auth: dict[str, str]) -> int:
    return int(client.get("/account/usage", headers=auth).json()["credits_balance"])


def test_unknown_length_is_measured_and_charged_after_download(
    client: TestClient, auth: dict[str, str], importer: FakeImporter, queued: list[uuid.UUID]
) -> None:
    from clipmaker.pipeline.runner import Outcome

    importer.duration = 0  # like the Apify actor's `"duration": null`
    project = _import(client, auth)
    assert project["state"] == "UPLOADED" and project["source_video"]["duration_seconds"] is None
    before = _credits(client, auth)
    assert client.post(f"/projects/{project['id']}/process", headers=auth).status_code == 202
    assert _credits(client, auth) == before  # not charged yet: length unknown
    assert _run(queued[-1], importer) == Outcome.PAUSED
    assert _credits(client, auth) == before - 1  # 12 s video → 1 credit, charged once
    _run(queued[-1], importer)
    assert _credits(client, auth) == before - 1


def test_too_short_after_measuring_is_rejected_without_charge(
    client: TestClient,
    auth: dict[str, str],
    importer: FakeImporter,
    queued: list[uuid.UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clipmaker.core.config import get_settings
    from clipmaker.pipeline.runner import Outcome

    importer.duration = 0
    pid = _import(client, auth)["id"]
    before = _credits(client, auth)
    client.post(f"/projects/{pid}/process", headers=auth)
    monkeypatch.setattr(get_settings(), "min_video_duration_seconds", 30)
    assert _run(queued[-1], importer) == Outcome.FAILED
    project = client.get(f"/projects/{pid}", headers=auth).json()
    assert "too short" in project["error_message"]
    assert "refunded" not in project["error_message"]  # nothing was charged
    assert _credits(client, auth) == before


def test_not_enough_credits_after_measuring(
    client: TestClient, auth: dict[str, str], importer: FakeImporter, queued: list[uuid.UUID]
) -> None:
    from clipmaker.db.models import User
    from clipmaker.db.session import get_session_factory
    from clipmaker.pipeline.runner import Outcome

    importer.duration = 0
    pid = _import(client, auth)["id"]
    client.post(f"/projects/{pid}/process", headers=auth)
    with get_session_factory()() as db:
        db.query(User).update({"credits_balance": 0})
        db.commit()
    assert _run(queued[-1], importer) == Outcome.FAILED
    message = client.get(f"/projects/{pid}", headers=auth).json()["error_message"]
    assert "credits" in message and "refunded" not in message
    status = client.get(f"/projects/{pid}/status", headers=auth).json()
    assert status["error_code"] == "insufficient_credits"
