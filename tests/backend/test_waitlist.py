"""The public waitlist endpoint, with the abuse and privacy behaviour it promises."""

from __future__ import annotations

from conftest import settings_patched
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from clipmaker.db.models import WaitlistSignup
from clipmaker.services import waitlist


def _join(client: TestClient, email: str, **extra: object) -> dict:
    res = client.post("/waitlist", json={"email": email, **extra})
    assert res.status_code == 201, res.text
    return res.json()


def test_join_returns_a_place_and_a_code(client: TestClient) -> None:
    first = _join(client, "ada@example.com")
    assert first["position"] == 1
    assert first["total"] == 1
    assert first["referral_code"]

    second = _join(client, "grace@example.com")
    assert second["position"] == 2
    assert second["referral_code"] != first["referral_code"]


def test_joining_twice_is_idempotent(client: TestClient, db: Session) -> None:
    first = _join(client, "ada@example.com")
    again = _join(client, "  ADA@Example.com  ")
    assert again["referral_code"] == first["referral_code"]
    assert again["position"] == first["position"]
    assert db.scalar(select(WaitlistSignup.email).where(WaitlistSignup.email == "ada@example.com"))
    assert waitlist.count(db) == 1


def test_referrals_move_you_up(client: TestClient) -> None:
    ada = _join(client, "ada@example.com")
    for i in range(12):
        _join(client, f"filler{i}@example.com")
    # Ada is 1st already, so use someone further down the list to see the jump.
    last = _join(client, "zoe@example.com")
    assert last["position"] == 14
    _join(client, "friend@example.com", referral_code=last["referral_code"])
    moved = _join(client, "zoe@example.com")
    assert moved["referrals"] == 1
    assert moved["position"] == 14 - waitlist.PLACES_PER_REFERRAL
    assert ada["referral_code"] != last["referral_code"]


def test_you_cannot_refer_yourself(client: TestClient, db: Session) -> None:
    ada = _join(client, "ada@example.com")
    _join(client, "ada@example.com", referral_code=ada["referral_code"])
    row = db.scalar(select(WaitlistSignup).where(WaitlistSignup.email == "ada@example.com"))
    assert row is not None
    assert row.referred_by_id is None


def test_an_unknown_referral_code_is_ignored(client: TestClient, db: Session) -> None:
    _join(client, "ada@example.com", referral_code="not-a-real-code")
    row = db.scalar(select(WaitlistSignup).where(WaitlistSignup.email == "ada@example.com"))
    assert row is not None
    assert row.referred_by_id is None


def test_the_honeypot_writes_nothing(client: TestClient, db: Session) -> None:
    res = client.post("/waitlist", json={"email": "bot@example.com", "company": "Acme"})
    assert res.status_code == 201  # looks exactly like success to the bot
    assert waitlist.count(db) == 0


def test_bad_addresses_and_unknown_fields_are_rejected(client: TestClient) -> None:
    assert client.post("/waitlist", json={"email": "not-an-email"}).status_code == 422
    assert client.post("/waitlist", json={}).status_code == 422
    assert (
        client.post("/waitlist", json={"email": "a@b.com", "is_admin": True}).status_code == 422
    )


def test_signups_from_one_machine_are_capped(client: TestClient) -> None:
    headers = {"x-forwarded-for": "203.0.113.9"}
    with settings_patched(waitlist_signups_per_hour=2):
        for i in range(2):
            res = client.post("/waitlist", json={"email": f"ok{i}@example.com"}, headers=headers)
            assert res.status_code == 201
        blocked = client.post("/waitlist", json={"email": "extra@example.com"}, headers=headers)
        assert blocked.status_code == 429
        # A different machine is unaffected.
        other = client.post(
            "/waitlist",
            json={"email": "elsewhere@example.com"},
            headers={"x-forwarded-for": "198.51.100.4"},
        )
        assert other.status_code == 201


def test_the_raw_ip_is_never_stored(client: TestClient, db: Session) -> None:
    client.post(
        "/waitlist",
        json={"email": "ada@example.com"},
        headers={"x-forwarded-for": "203.0.113.9"},
    )
    row = db.scalar(select(WaitlistSignup).where(WaitlistSignup.email == "ada@example.com"))
    assert row is not None
    assert row.ip_hash and "203.0.113.9" not in row.ip_hash
    assert len(row.ip_hash) == 64


def test_the_same_address_hashes_differently_under_a_different_key() -> None:
    assert waitlist.hash_ip("203.0.113.9", "key-one") != waitlist.hash_ip("203.0.113.9", "key-two")
    assert waitlist.hash_ip(None, "key-one") is None


def test_export_is_owner_only(
    client: TestClient, auth: dict[str, str], other_auth: dict[str, str]
) -> None:
    _join(client, "ada@example.com")

    assert client.get("/waitlist/export").status_code == 401  # anonymous

    with settings_patched(owner_emails="alice@example.com"):
        # A signed-in non-owner is told the endpoint doesn't exist, not that it's forbidden.
        assert client.get("/waitlist/export", headers=other_auth).status_code == 404

        allowed = client.get("/waitlist/export", headers=auth)
        assert allowed.status_code == 200
        assert [row["email"] for row in allowed.json()] == ["ada@example.com"]
