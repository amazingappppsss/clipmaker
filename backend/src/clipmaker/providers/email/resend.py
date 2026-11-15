"""Resend implementation of EmailSender (REST, via httpx).

Resend was chosen for the free tier and because it needs nothing but an API key and a verified
sending domain — no SMTP credentials to leak and no server to run. Swapping it means writing
one more class against `EmailSender`; nothing outside this module knows the API shape.

Until a domain is verified, `RESEND_FROM` can stay on Resend's own onboarding sender, which
only delivers to the account owner's address. That's enough to prove the pipeline end to end
before paying for a domain.
"""

from __future__ import annotations

import logging

import httpx

from clipmaker.core.config import Settings
from clipmaker.providers.email.base import Email, EmailError

logger = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"
TIMEOUT_SECONDS = 15.0

#: Resend returns these when the problem is transient and the same request may succeed later.
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class ResendSender:
    """Sends one message per request. No batching: our volume doesn't need it."""

    def __init__(self, settings: Settings) -> None:
        key = settings.resend_api_key
        self._key = key.get_secret_value() if key else None
        self._from = settings.email_from
        self._reply_to = settings.email_reply_to or None

    @property
    def ready(self) -> bool:
        return bool(self._key and self._from)

    def send(self, message: Email) -> None:
        if not self.ready:
            raise EmailError(
                "Resend is not configured (RESEND_API_KEY / EMAIL_FROM)", retryable=False
            )

        payload: dict[str, object] = {
            "from": self._from,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
        }
        if message.html:
            payload["html"] = message.html
        reply_to = message.reply_to or self._reply_to
        if reply_to:
            payload["reply_to"] = reply_to

        try:
            response = httpx.post(
                API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._key}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise EmailError(f"Could not reach the email provider: {exc}", retryable=True) from exc

        if response.status_code >= 400:
            # Resend's message says *why* (unverified domain, test-mode recipient, bad key),
            # which is the whole diagnosis. The recipient is stripped out of it first, so the
            # reason can be shown on /health without leaking who it was for.
            detail = ""
            try:
                body = response.json()
                detail = str(body.get("message") or body.get("error") or "")[:200]
            except ValueError:
                detail = ""
            detail = detail.replace(message.to, "<recipient>")
            raise EmailError(
                f"Email provider refused the message (HTTP {response.status_code})"
                + (f": {detail}" if detail else ""),
                retryable=response.status_code in _RETRYABLE_STATUS,
            )
