"""Processing API: start/retry rules, credits, status and isolation."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from conftest import upload_project


def test_process_requires_upload(
    client: TestClient, auth: dict[str, str], queued: list[uuid.UUID]
) -> None:
    pid = client.post("/projects", json={"title": "x"}, headers=auth).json()["id"]
    res = client.post(f"/projects/{pid}/process", headers=auth)
    assert res.status_code == 409 and queued == []


def test_process_debits_and_queues(
    client: TestClient, auth: dict[str, str], sample_video: Path, queued: list[uuid.UUID]
) -> None:
    pid = upload_project(client, auth, sample_video)
    res = client.post(f"/projects/{pid}/process", headers=auth)
    assert res.status_code == 202 and res.json()["state"] == "INGESTING"
    assert len(queued) == 1
    usage = client.get("/account/usage", headers=auth).json()
    assert usage["credits_balance"] == 14
    assert usage["history"][0]["kind"] == "debit"
    # Cannot start twice while running.
    assert client.post(f"/projects/{pid}/process", headers=auth).status_code == 409
    status = client.get(f"/projects/{pid}/status", headers=auth).json()
    assert status["project_state"] == "INGESTING"
    assert status["stages"][0]["stage"] == "INGESTING"
    assert client.get(f"/projects/{pid}/clips", headers=auth).json() == []


def test_insufficient_credits(
    client: TestClient, auth: dict[str, str], sample_video: Path, queued: list[uuid.UUID]
) -> None:
    from clipmaker.db.models import User
    from clipmaker.db.session import get_session_factory

    pid = upload_project(client, auth, sample_video)
    with get_session_factory()() as db:
        user = db.query(User).one()
        user.credits_balance = 0
        db.commit()
    res = client.post(f"/projects/{pid}/process", headers=auth)
    assert res.status_code == 402 and res.json()["code"] == "insufficient_credits"
    assert queued == []


def test_other_user_cannot_process_or_read(
    client: TestClient,
    auth: dict[str, str],
    other_auth: dict[str, str],
    sample_video: Path,
    queued: list[uuid.UUID],
) -> None:
    pid = upload_project(client, auth, sample_video)
    for method, path in [("post", "process"), ("get", "status"), ("get", "clips")]:
        assert (
            getattr(client, method)(f"/projects/{pid}/{path}", headers=other_auth).status_code
            == 404
        )
