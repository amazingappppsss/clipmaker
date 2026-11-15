"""Select the configured email sender."""

from __future__ import annotations

from functools import lru_cache

from clipmaker.core.config import Settings, get_settings
from clipmaker.providers.email.base import EmailSender, NullSender


def build_email_sender(settings: Settings) -> EmailSender:
    """Return the sender named by `EMAIL_PROVIDER`, or a no-op one when it can't deliver.

    An unconfigured provider is not an error: a deployment without an email key must still
    accept signups. It reports `ready = False`, which /health surfaces.
    """
    if settings.email_provider == "resend":
        from clipmaker.providers.email.resend import ResendSender

        sender = ResendSender(settings)
        return sender if sender.ready else NullSender()
    return NullSender()


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    """Process-wide sender (httpx calls are stateless, so one instance is fine)."""
    return build_email_sender(get_settings())
