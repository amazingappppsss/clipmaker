"""Shared pytest fixtures.

Tests run against a real PostgreSQL database (TEST_DATABASE_URL, migrated with Alembic) and
real FFmpeg-generated media — the same code paths as production, nothing faked except the
rate-limit counter (in-memory) and the storage root (a temp directory).
"""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://clipmaker:clipmaker@localhost:5432/clipmaker_test"
)
_STORAGE_DIR = Path(os.environ.get("TEST_STORAGE_DIR", "/tmp/clipmaker-test-storage"))

# Configure the app *before* anything imports clipmaker settings.
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": TEST_DB,
        "SUPABASE_JWT_SECRET": "test-secret-that-is-long-enough-for-hs256",
        "SUPABASE_URL": "",
        "ENABLE_DEV_AUTH": "true",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(_STORAGE_DIR),
        "API_PUBLIC_URL": "http://testserver",
        "RENDER_PRESET": "ultrafast",
        "MIN_VIDEO_DURATION_SECONDS": "5",
        "WORK_DIR": "/tmp/clipmaker-test-work",
        "ANTHROPIC_API_KEY": "",
        "ASSEMBLYAI_API_KEY": "",
        "WAITLIST_SIGNUPS_PER_HOUR": "100",
    }
)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from clipmaker.core.config import get_settings  # noqa: E402
from clipmaker.core.rate_limit import get_counter  # noqa: E402
from clipmaker.core.security import mint_dev_token  # noqa: E402
from clipmaker.db.session import get_engine, get_session_factory  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


class MemoryCounter:
    """In-memory replacement for the Redis rate-limit counter."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def incr_window(self, key: str, window_seconds: int) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    """Reset the test schema and apply all migrations once per test session."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "src/clipmaker/db/migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    """Truncate every table between tests for isolation."""
    yield
    with get_engine().begin() as conn:
        tables = conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename <> 'alembic_version'"
            )
        ).scalars()
        conn.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    """A session for direct service-level tests."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def counter() -> MemoryCounter:
    return MemoryCounter()


@pytest.fixture
def client(counter: MemoryCounter) -> Iterator[TestClient]:
    """API client with the in-memory rate-limit counter."""
    from clipmaker.main import app

    app.dependency_overrides[get_counter] = lambda: counter
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_token(email: str = "alice@example.com", user_id: uuid.UUID | None = None) -> str:
    return mint_dev_token(user_id or uuid.uuid5(uuid.NAMESPACE_URL, email), email, get_settings())


@pytest.fixture
def auth() -> dict[str, str]:
    """Authorization header for user Alice."""
    return {"Authorization": f"Bearer {make_token('alice@example.com')}"}


@pytest.fixture
def other_auth() -> dict[str, str]:
    """Authorization header for a different user, Bob."""
    return {"Authorization": f"Bearer {make_token('bob@example.com')}"}


def _ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("media")


@pytest.fixture(scope="session")
def sample_video(media_dir: Path) -> Path:
    """A 12 s 1280x720 MP4 with a tone audio track."""
    out = media_dir / "sample.mp4"
    _ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=30:duration=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=12",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def podcast_video(media_dir: Path) -> Path:
    """A 9.5-minute low-res video with audio: long enough for the fake transcript's clips."""
    out = media_dir / "podcast.mp4"
    _ffmpeg(
        [
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15:duration=570",
            "-f", "lavfi", "-i", "sine=frequency=220:duration=570",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(out),
        ]
    )  # fmt: skip
    return out


@pytest.fixture(scope="session")
def silent_video(media_dir: Path) -> Path:
    """A video without any audio stream."""
    out = media_dir / "silent.mp4"
    _ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=25:duration=8",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def short_video(media_dir: Path) -> Path:
    """A 2 s video — below the minimum duration configured for tests (5 s)."""
    out = media_dir / "short.mp4"
    _ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=25:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=2",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
    )
    return out


@pytest.fixture
def queued(client: TestClient) -> list[uuid.UUID]:
    """Capture enqueued job ids instead of sending them to Celery."""
    from clipmaker.api.deps import get_job_queue
    from clipmaker.main import app

    jobs: list[uuid.UUID] = []
    app.dependency_overrides[get_job_queue] = lambda: jobs.append
    return jobs


def upload_project(client: TestClient, auth: dict[str, str], video: Path) -> str:
    pid = client.post("/projects", json={"title": "Pod"}, headers=auth).json()["id"]
    ticket = client.post(
        f"/projects/{pid}/upload",
        headers=auth,
        json={
            "filename": video.name,
            "content_type": "video/mp4",
            "size_bytes": video.stat().st_size,
        },
    ).json()
    url = ticket["upload_url"].removeprefix("http://testserver")
    assert client.put(url, content=video.read_bytes(), headers=ticket["headers"]).status_code == 204
    assert client.post(f"/projects/{pid}/upload/complete", headers=auth).status_code == 200
    return pid
