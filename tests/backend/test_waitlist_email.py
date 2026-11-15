"""The waitlist welcome email, and the owner-only removal."""

from __future__ import annotations

import json

import pytest
from conftest import settings_patched
from fastapi.testclient import TestClient

from clipmaker.core.config import Settings
from clipmaker.providers.email.base import Email, EmailError, NullSender
from clipmaker.providers.email.factory import build_email_sender
from clipmaker.services.waitlist import WaitlistPlace
from clipmaker.services.waitlist_email import send_welcome, welcome_html, welcome_text

PLACE = WaitlistPlace(
    position=7, referral_code="abc123", referrals=2, total=40, is_new=True
)


class Recorder:
    """A sender that remembers what it was asked to send."""

    def __init__(self, *, ready: bool = True, fail: Exception | None = None) -> None:
        self._ready = ready
        self._fail = fail
        self.sent: list[Email] = []

    @property
    def ready(self) -> bool:
        return self._ready

    def send(self, message: Email) -> None:
        if self._fail:
            raise self._fail
        self.sent.append(message)


def test_the_email_carries_the_place_and_a_working_referral_link() -> None:
    text = welcome_text(PLACE, "https://clip2easy.vercel.app")
    html = welcome_html(PLACE, "https://clip2easy.vercel.app")
    for body in (text, html):
        assert "#7" in body or ">#7" in body or "7" in body
        assert "https://clip2easy.vercel.app/waitlist?ref=abc123" in body
    # A trailing slash on the site URL must not produce a doubled one.
    assert "https://a.app/waitlist?ref=abc123" in welcome_text(PLACE, "https://a.app/")


def test_the_html_body_uses_inline_styles_only() -> None:
    """Email clients strip <style> blocks and ignore classes."""
    html = welcome_html(PLACE, "https://clip2easy.vercel.app")
    assert "<style" not in html
    assert 'class="' not in html


@pytest.mark.parametrize(
    "sender",
    [
        Recorder(ready=False),
        Recorder(fail=EmailError("provider down", retryable=True)),
        Recorder(fail=RuntimeError("provider bug")),
        NullSender(),
    ],
)
def test_a_failed_send_never_raises(sender: object) -> None:
    """The signup is already committed; losing the email must not lose the row."""
    assert send_welcome(sender, "a@b.com", PLACE, "https://x.app") is False  # type: ignore[arg-type]


def test_a_good_send_reports_success_and_goes_to_the_right_address() -> None:
    sender = Recorder()
    assert send_welcome(sender, "ada@example.com", PLACE, "https://x.app") is True
    assert len(sender.sent) == 1
    assert sender.sent[0].to == "ada@example.com"
    assert sender.sent[0].text and sender.sent[0].html


def test_no_key_means_no_sender_rather_than_a_broken_one() -> None:
    assert build_email_sender(Settings()).ready is False
    assert build_email_sender(Settings(resend_api_key="re_x")).ready is True
    assert build_email_sender(Settings(email_provider="nope")).ready is False


def test_health_reports_whether_email_can_be_sent(client: TestClient) -> None:
    assert client.get("/health").json()["email_ready"] is False


def test_removal_is_owner_only(
    client: TestClient, auth: dict[str, str], other_auth: dict[str, str]
) -> None:
    client.post("/waitlist", json={"email": "ada@example.com"})
    assert client.get("/waitlist/stats").json()["total"] == 1

    assert client.delete("/waitlist/ada@example.com").status_code == 401  # anonymous

    with settings_patched(owner_emails="alice@example.com"):
        # A signed-in non-owner is told it doesn't exist, not that it's forbidden.
        assert client.delete("/waitlist/ada@example.com", headers=other_auth).status_code == 404

        assert client.delete("/waitlist/ADA@example.com", headers=auth).status_code == 204
        assert client.get("/waitlist/stats").json()["total"] == 0

        # Deleting it again is a 404, not a crash.
        assert client.delete("/waitlist/ada@example.com", headers=auth).status_code == 404


def test_removing_a_referrer_leaves_their_referrals_in_place(
    client: TestClient, auth: dict[str, str]
) -> None:
    referrer = client.post("/waitlist", json={"email": "ada@example.com"}).json()
    client.post(
        "/waitlist",
        json={"email": "friend@example.com", "referral_code": referrer["referral_code"]},
    )
    with settings_patched(owner_emails="alice@example.com"):
        assert client.delete("/waitlist/ada@example.com", headers=auth).status_code == 204
    assert client.get("/waitlist/stats").json()["total"] == 1


@pytest.mark.parametrize(
    "name", ["RESEND_API_KEY", "RESEND_KEY", "RESEND_TOKEN", "EMAIL_API_KEY"]
)
def test_the_key_is_found_under_any_of_the_obvious_names(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A key pasted under a near-miss name silently sends no mail; accept the variants."""
    for other in ("RESEND_API_KEY", "RESEND_KEY", "RESEND_TOKEN", "EMAIL_API_KEY"):
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(name, '  "re_abc123"  ')  # dashboards paste quotes and spaces
    settings = Settings()
    assert settings.resend_api_key is not None
    assert settings.resend_api_key.get_secret_value() == "re_abc123"
    assert build_email_sender(settings).ready is True


def test_health_lists_email_variable_names_but_never_values(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A key on the wrong service is invisible; names make that diagnosable, values would leak."""
    monkeypatch.setenv("RESEND_API_KEY", "re_supersecret")
    monkeypatch.setenv("EMAIL_FROM", "Clip2Easy <hi@example.com>")
    monkeypatch.setenv("UNRELATED_THING", "x")
    body = client.get("/health").json()
    seen = body["email_env_seen"]
    assert "RESEND_API_KEY" in seen
    assert "EMAIL_FROM" in seen
    assert "UNRELATED_THING" not in seen
    assert "re_supersecret" not in json.dumps(body)
