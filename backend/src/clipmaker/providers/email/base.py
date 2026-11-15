"""Email sending interface.

Kept behind a Protocol for the same reason as the other providers: the sender can be swapped
through configuration. Nothing in the app composes provider-specific payloads.

A send is never allowed to break the thing that triggered it. Someone joining the waitlist has
already been written to the database by the time we try to email them, so a failure here is
logged and swallowed — losing a welcome email is an annoyance, losing the signup is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EmailError(Exception):
    """A send failed. `retryable` marks transient failures (timeouts, 5xx, rate limits)."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class Email:
    """One message. `text` is required; `html` is optional but strongly preferred."""

    to: str
    subject: str
    text: str
    html: str | None = None
    reply_to: str | None = None


class EmailSender(Protocol):
    """What every sender must do."""

    @property
    def ready(self) -> bool:
        """True when this sender is configured enough to actually deliver."""
        ...

    def send(self, message: Email) -> None:
        """Deliver one message, or raise EmailError."""
        ...


class NullSender:
    """Used when no provider is configured: records nothing, delivers nothing, never raises.

    This is the default, so a deployment without an email key keeps working — signups are
    still stored, they just aren't written to yet. `ready` is False so /health says so
    plainly instead of the absence being discovered when nobody gets their invite.
    """

    @property
    def ready(self) -> bool:
        return False

    def send(self, message: Email) -> None:
        raise EmailError("No email provider is configured", retryable=False)
