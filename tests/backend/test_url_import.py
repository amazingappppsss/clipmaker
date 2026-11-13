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
    from pipeline_fakes import FakeLLM, FakeTranscriber

    runner = JobRunner(
        job_id,
        "w",
        get_settings(),
        get_storage(),
        get_session_factory(),
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
