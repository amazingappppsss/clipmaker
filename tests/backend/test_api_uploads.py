"""Upload flow end-to-end through the API with real files and real ffprobe."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient


def _project(client: TestClient, auth: dict[str, str]) -> str:
    return client.post("/projects", json={"title": "Upload test"}, headers=auth).json()["id"]


def _ticket(client: TestClient, auth: dict[str, str], pid: str, path: Path, **kw: object) -> dict:
    body = {
        "filename": path.name,
        "content_type": "video/mp4",
        "size_bytes": path.stat().st_size,
        **kw,
    }
    res = client.post(f"/projects/{pid}/upload", json=body, headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


def _put(client: TestClient, ticket: dict, data: bytes) -> int:
    url = urlparse(ticket["upload_url"])
    return client.put(
        f"{url.path}?{url.query}", content=data, headers=ticket["headers"]
    ).status_code


def test_full_upload_flow(client: TestClient, auth: dict[str, str], sample_video: Path) -> None:
    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, sample_video)
    assert _put(client, ticket, sample_video.read_bytes()) == 204

    res = client.post(f"/projects/{pid}/upload/complete", headers=auth)
    assert res.status_code == 200, res.text
    project = res.json()
    assert project["state"] == "UPLOADED"
    src = project["source_video"]
    assert src["upload_status"] == "verified"
    assert (src["width"], src["height"]) == (1280, 720)
    assert src["has_audio"] is True
    assert project["source_video_url"] is not None


def test_complete_without_bytes_fails(
    client: TestClient, auth: dict[str, str], sample_video: Path
) -> None:
    pid = _project(client, auth)
    _ticket(client, auth, pid, sample_video)
    res = client.post(f"/projects/{pid}/upload/complete", headers=auth)
    assert res.status_code == 422
    assert res.json()["code"] == "upload_missing"


def test_put_larger_than_signed_size_rejected(
    client: TestClient, auth: dict[str, str], sample_video: Path
) -> None:
    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, sample_video)
    assert _put(client, ticket, sample_video.read_bytes() + b"extra") == 422


def test_tampered_signature_rejected(
    client: TestClient, auth: dict[str, str], sample_video: Path
) -> None:
    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, sample_video)
    ticket["upload_url"] = ticket["upload_url"].replace("sig=", "sig=0")
    assert _put(client, ticket, sample_video.read_bytes()) == 403


def test_unsupported_type_and_extension(client: TestClient, auth: dict[str, str]) -> None:
    pid = _project(client, auth)
    bad_type = {"filename": "a.avi", "content_type": "video/x-msvideo", "size_bytes": 10}
    res = client.post(f"/projects/{pid}/upload", json=bad_type, headers=auth)
    assert res.json()["code"] == "unsupported_type"
    mismatch = {"filename": "a.mov", "content_type": "video/mp4", "size_bytes": 10}
    res = client.post(f"/projects/{pid}/upload", json=mismatch, headers=auth)
    assert res.json()["code"] == "extension_mismatch"


def test_video_without_audio_rejected(
    client: TestClient, auth: dict[str, str], silent_video: Path
) -> None:
    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, silent_video)
    _put(client, ticket, silent_video.read_bytes())
    res = client.post(f"/projects/{pid}/upload/complete", headers=auth)
    assert res.json()["code"] == "no_audio"
    project = client.get(f"/projects/{pid}", headers=auth).json()
    assert project["state"] == "CREATED"
    assert project["source_video"]["upload_status"] == "failed"


def test_too_short_rejected(client: TestClient, auth: dict[str, str], short_video: Path) -> None:
    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, short_video)
    _put(client, ticket, short_video.read_bytes())
    assert (
        client.post(f"/projects/{pid}/upload/complete", headers=auth).json()["code"] == "too_short"
    )


def test_corrupt_file_rejected(client: TestClient, auth: dict[str, str], tmp_path: Path) -> None:
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"\x00" * 4096)
    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, junk)
    _put(client, ticket, junk.read_bytes())
    res = client.post(f"/projects/{pid}/upload/complete", headers=auth)
    assert res.json()["code"] == "unreadable_video"


def test_delete_removes_stored_files(
    client: TestClient, auth: dict[str, str], sample_video: Path
) -> None:
    from clipmaker.storage.factory import get_storage

    pid = _project(client, auth)
    ticket = _ticket(client, auth, pid, sample_video)
    _put(client, ticket, sample_video.read_bytes())
    key = urlparse(ticket["upload_url"]).path.removeprefix("/storage/local/")
    assert get_storage().head(key) is not None
    client.delete(f"/projects/{pid}", headers=auth)
    assert get_storage().head(key) is None


def test_upload_url_follows_request_host_when_public_url_unset(
    client: TestClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Single-node deploys need no API_PUBLIC_URL: links use the proxy's forwarded host."""
    from clipmaker.storage.factory import get_storage

    store = get_storage()
    monkeypatch.setattr(store, "_base", None)
    pid = client.post("/projects", json={"title": "t"}, headers=auth).json()["id"]
    body = {"filename": "a.mp4", "content_type": "video/mp4", "size_bytes": 10}
    headers = {**auth, "x-forwarded-proto": "https", "x-forwarded-host": "api.example.com"}
    ticket = client.post(f"/projects/{pid}/upload", json=body, headers=headers).json()
    assert ticket["upload_url"].startswith("https://api.example.com/storage/local/")
    plain = client.post(f"/projects/{pid}/upload", json=body, headers=auth).json()
    assert plain["upload_url"].startswith("http://testserver/storage/local/")
