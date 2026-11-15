"""The emails the waitlist sends.

One message, sent once, when someone joins. No drip sequence — the page promises "one email
when your spot opens" and nothing else, so this confirms the spot and then stays quiet.

Sending never breaks signing up: `send_welcome` swallows every failure after logging it. The
row is already committed by the time it runs, and a lost welcome email is recoverable (we can
re-send from the export) while a lost signup is not.
"""

from __future__ import annotations

import html
import logging

from clipmaker.providers.email.base import Email, EmailError, EmailSender
from clipmaker.services.waitlist import PLACES_PER_REFERRAL, WaitlistPlace

logger = logging.getLogger(__name__)

SUBJECT = "You're in — here's your spot"


def _share_url(base_url: str, code: str) -> str:
    return f"{base_url.rstrip('/')}/waitlist?ref={code}"


def welcome_text(place: WaitlistPlace, base_url: str) -> str:
    """Plain-text body. Always sent, because some clients never render the HTML part."""
    link = _share_url(base_url, place.referral_code)
    return (
        f"You're #{place.position} on the Clip2Easy waitlist.\n\n"
        "Here's what you get as a founding member:\n"
        "  - We clip your first episode by hand, free, before launch\n"
        "  - Founding price locked for life\n"
        "  - 100 free minutes at launch instead of 15\n\n"
        "Want it sooner? Every friend who joins on your link moves you up "
        f"{PLACES_PER_REFERRAL} places:\n"
        f"  {link}\n\n"
        "We'll email you once when your spot opens. That's the only one you'll get.\n\n"
        "- Clip2Easy\n"
    )


def welcome_html(place: WaitlistPlace, base_url: str) -> str:
    """HTML body. Inline styles only: email clients strip <style> blocks and ignore classes."""
    link = html.escape(_share_url(base_url, place.referral_code))
    return f"""\
<!doctype html>
<html><body style="margin:0;padding:24px;background:#f3f4f8;
 font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0b0b12">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:18px;padding:32px">
    <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:.08em;
     text-transform:uppercase;color:#1e3bea">You&rsquo;re in</p>
    <p style="margin:8px 0 0;font-size:40px;font-weight:800;line-height:1">
      #{place.position}
      <span style="font-size:15px;font-weight:600;color:#6b6e80">of {place.total}</span>
    </p>
    <p style="margin:20px 0 0;font-size:15px;line-height:1.6">
      You&rsquo;re a founding member of Clip2Easy. That means:
    </p>
    <ul style="margin:12px 0 0;padding-left:20px;font-size:15px;line-height:1.7">
      <li>We clip your first episode <strong>by hand, free</strong>, before launch</li>
      <li>Your price is <strong>locked at half off, for life</strong></li>
      <li><strong>100 free minutes</strong> at launch instead of 15</li>
    </ul>
    <p style="margin:24px 0 0;font-size:15px;line-height:1.6">
      Want your free episode sooner? Every friend who joins on your link moves you up
      <strong>{PLACES_PER_REFERRAL} places</strong>.
    </p>
    <p style="margin:16px 0 0">
      <a href="{link}" style="display:inline-block;background:#c8ff2e;color:#0b0b12;
       text-decoration:none;font-weight:800;padding:12px 22px;border-radius:999px">
        Share your link</a>
    </p>
    <p style="margin:24px 0 0;font-size:13px;color:#6b6e80;line-height:1.6">
      We&rsquo;ll email you once when your spot opens. That&rsquo;s the only one you&rsquo;ll get.
    </p>
  </div>
</body></html>
"""


def send_welcome(sender: EmailSender, to: str, place: WaitlistPlace, base_url: str) -> bool:
    """Send the welcome email. Returns whether it went out; never raises."""
    if not sender.ready:
        logger.info("waitlist_email_skipped", extra={"reason": "no_provider"})
        return False
    try:
        sender.send(
            Email(
                to=to,
                subject=SUBJECT,
                text=welcome_text(place, base_url),
                html=welcome_html(place, base_url),
            )
        )
    except EmailError as exc:
        # The address is never logged; the export is how we'd find who to re-send to.
        logger.warning(
            "waitlist_email_failed", extra={"retryable": exc.retryable, "error": str(exc)}
        )
        return False
    except Exception:  # a provider bug must not cost us the signup
        logger.exception("waitlist_email_crashed")
        return False
    return True
