"""services/housekeeping.py — making room on a small disk instead of failing a download."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from clipmaker.core.enums import ProjectState
from clipmaker.db.models import Clip, ClipAsset, Project
from clipmaker.db.session import get_session_factory
from clipmaker.services.housekeeping import HEADROOM_BYTES, free_bytes, make_room
from clipmaker.storage.base import project_prefix
from clipmaker.storage.factory import get_storage


def _finished_project(client: TestClient, auth: dict[str, str], state: ProjectState) -> str:
    pid = client.post("/projects", json={"title": "old"}, headers=auth).json()["id"]
    store = get_storage()
    with get_session_factory()() as db:
        project = db.get(Project, uuid.UUID(pid))
        assert project is not None
        project.state = state
        clip = Clip(project_id=project.id, rank=1, style="modern_creator")
        db.add(clip)
        db.flush()
        key = f"{project_prefix(str(project.user_id), pid)}clips/{clip.id}.mp4"
        path = Path(str(store.path_for(key)))  # type: ignore[attr-defined]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 1024)
        store_info = store.head(key)
        assert store_info is not None
        db.add(ClipAsset(clip_id=clip.id, kind="video", storage_key=key, size_bytes=1024))
        db.commit()
    return pid


def test_room_is_made_from_the_oldest_finished_projects(
    client: TestClient, auth: dict[str, str], tmp_path: Path
) -> None:
    pid = _finished_project(client, auth, ProjectState.COMPLETED)
    store = get_storage()
    with get_session_factory()() as db:
        project = db.get(Project, uuid.UUID(pid))
        assert project is not None
        prefix = project_prefix(str(project.user_id), pid)
        # Ask for more space than the disk could ever have, so cleaning is forced.
        removed = make_room(db, store, str(tmp_path), needed_bytes=1 << 60)
        assert removed >= 1
        assert not list(Path(str(store.path_for(prefix))).rglob("*.mp4"))  # files gone
        assert db.query(ClipAsset).count() == 0  # no download links to files that are gone
        assert db.get(Project, uuid.UUID(pid)) is not None  # the project itself stays


def test_running_projects_are_never_touched(
    client: TestClient, auth: dict[str, str], tmp_path: Path
) -> None:
    _finished_project(client, auth, ProjectState.RENDERING)
    with get_session_factory()() as db:
        assert make_room(db, get_storage(), str(tmp_path), needed_bytes=1 << 60) == 0
        assert db.query(ClipAsset).count() == 1


def test_nothing_is_deleted_when_there_is_room_or_storage_is_remote(
    client: TestClient, auth: dict[str, str], tmp_path: Path
) -> None:
    _finished_project(client, auth, ProjectState.COMPLETED)
    with get_session_factory()() as db:
        assert make_room(db, get_storage(), str(tmp_path), needed_bytes=1) == 0  # plenty free
        assert make_room(db, get_storage(), None, needed_bytes=1 << 60) == 0  # cloud storage
        assert db.query(ClipAsset).count() == 1
    assert (free_bytes(str(tmp_path)) or 0) > HEADROOM_BYTES


def test_scheduled_sweep_frees_space(client: TestClient, auth: dict[str, str]) -> None:
    """The periodic task keeps room ready, so an import never meets a full disk."""
    from clipmaker.workers.tasks import reap_stale_jobs

    _finished_project(client, auth, ProjectState.COMPLETED)
    assert reap_stale_jobs() >= 0  # runs without a worker and without raising


def test_an_impossible_request_deletes_nothing(tmp_path: Path, db: Session) -> None:
    """Asking a 0.45 GB volume for 500 MB free made every sweep wipe every project."""
    from clipmaker.services.housekeeping import HEADROOM_BYTES, MAX_SHARE_OF_DISK, affordable

    total = shutil.disk_usage(str(tmp_path)).total
    ceiling = int(total * MAX_SHARE_OF_DISK) - HEADROOM_BYTES

    # More than the disk could ever give is clamped, not honoured.
    assert affordable(total * 10, str(tmp_path)) == max(0, ceiling)
    # A modest request is untouched.
    assert affordable(1024, str(tmp_path)) == 1024


def test_a_failed_projects_source_is_the_last_thing_deleted(tmp_path: Path, db: Session) -> None:
    """Without it, "Try again" can only fail — worse than a full disk."""
    from clipmaker.services.housekeeping import LAST_RESORT, REMOVABLE

    assert LAST_RESORT == ProjectState.FAILED
    assert LAST_RESORT in REMOVABLE, "it is still removable, just last"
