"""Project API — auth, isolation, pagination, deletion, rate limiting, health."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create(client: TestClient, auth: dict[str, str], title: str = "Episode 1") -> dict:
    res = client.post("/projects", json={"title": title}, headers=auth)
    assert res.status_code == 201, res.text
    return res.json()


def test_requires_auth(client: TestClient) -> None:
    res = client.get("/projects")
    assert res.status_code == 401
    assert res.json()["code"] == "unauthorized"


def test_create_with_defaults(client: TestClient, auth: dict[str, str]) -> None:
    project = _create(client, auth)
    assert project["state"] == "CREATED"
    assert project["settings"] == {
        "category": "auto",
        "language": "auto",
        "clip_count": "auto",
        "style": "auto",
    }


def test_create_validates_settings(client: TestClient, auth: dict[str, str]) -> None:
    res = client.post("/projects", json={"title": "x", "settings": {"clip_count": 7}}, headers=auth)
    assert res.status_code == 422
    res = client.post("/projects", json={"title": "  "}, headers=auth)
    assert res.status_code == 422


def test_users_cannot_see_each_other(
    client: TestClient, auth: dict[str, str], other_auth: dict[str, str]
) -> None:
    project = _create(client, auth)
    assert client.get(f"/projects/{project['id']}", headers=other_auth).status_code == 404
    assert client.delete(f"/projects/{project['id']}", headers=other_auth).status_code == 404
    assert client.get("/projects", headers=other_auth).json()["items"] == []


def test_pagination(client: TestClient, auth: dict[str, str]) -> None:
    for i in range(5):
        _create(client, auth, f"P{i}")
    first = client.get("/projects?limit=2", headers=auth).json()
    second = client.get(f"/projects?limit=2&cursor={first['next_cursor']}", headers=auth).json()
    third = client.get(f"/projects?limit=2&cursor={second['next_cursor']}", headers=auth).json()
    titles = [p["title"] for page in (first, second, third) for p in page["items"]]
    assert titles == ["P4", "P3", "P2", "P1", "P0"]
    assert third["next_cursor"] is None


def test_delete(client: TestClient, auth: dict[str, str]) -> None:
    project = _create(client, auth)
    assert client.delete(f"/projects/{project['id']}", headers=auth).status_code == 204
    assert client.get(f"/projects/{project['id']}", headers=auth).status_code == 404


def test_account_usage_shows_trial(client: TestClient, auth: dict[str, str]) -> None:
    usage = client.get("/account/usage", headers=auth).json()
    assert usage["credits_balance"] == 15
    assert usage["history"][0]["kind"] == "grant"
    assert [p["plan"] for p in usage["plans"]] == ["free", "starter", "pro"]


def test_rate_limit(client: TestClient, auth: dict[str, str], counter: object) -> None:
    from clipmaker.core.config import get_settings

    limit = get_settings().rate_limit_per_minute
    for _ in range(limit):
        client.get("/projects", headers=auth)
    res = client.get("/projects", headers=auth)
    assert res.status_code == 429


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["database"] is True
    # Readiness flags are booleans only; key values never appear in the response.
    assert {"transcription_ready", "llm_ready", "link_import_ready"} <= body.keys()
    assert all(isinstance(body[k], bool) for k in ("transcription_ready", "llm_ready"))


def test_public_plans(client: TestClient) -> None:
    plans = client.get("/plans").json()
    assert [p["price_usd_cents"] for p in plans] == [0, 1500, 2900]
