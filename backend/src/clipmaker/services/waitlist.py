"""Pre-launch waitlist.

Security notes, because this is the one endpoint the whole internet can reach unauthenticated:

* **No raw IPs.** The caller's address is stored only as a keyed HMAC, so we can count
  signups per machine without holding addresses we'd then have to protect.
* **Idempotent.** Signing up twice returns the same position and code, and never re-assigns
  the referrer — otherwise someone could farm referrals by re-submitting other people's
  addresses.
* **No self-referral.** A code that resolves to the signup being created is ignored.
* **Membership is low-sensitivity but not nothing.** The response shape is identical for a
  new and an existing address, so the endpoint doesn't *announce* membership, though a
  determined prober could infer it from the position. The real defence is the per-IP rate
  limit in the API layer; we accept that trade for a waitlist, which holds no secrets.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from clipmaker.db.models import WaitlistSignup

#: How many founding members get the full pre-launch offer. The page counts down to this.
FOUNDING_SPOTS = 100

#: Each friend who joins on your link moves you this many places up the list.
PLACES_PER_REFERRAL = 10

_CODE_BYTES = 6  # ~8 url-safe characters
_MAX_CODE_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class WaitlistPlace:
    """What we tell someone about their spot. Contains no data about anyone else."""

    position: int
    referral_code: str
    referrals: int
    total: int
    is_new: bool


def hash_ip(ip: str | None, key: str) -> str | None:
    """A keyed, non-reversible fingerprint of an address (None when we don't have one)."""
    if not ip:
        return None
    return hmac.new(key.encode(), ip.encode(), hashlib.sha256).hexdigest()


def normalize_email(email: str) -> str:
    """Lowercase and strip. Pydantic has already checked the shape."""
    return email.strip().lower()


def _new_code(db: Session) -> str:
    """An unguessable short code, retried on the (vanishingly rare) collision."""
    for _ in range(_MAX_CODE_ATTEMPTS):
        code = secrets.token_urlsafe(_CODE_BYTES)
        if db.scalar(select(WaitlistSignup.id).where(WaitlistSignup.referral_code == code)) is None:
            return code
    raise RuntimeError("Could not allocate a referral code")


def _referrals(db: Session, signup_id: uuid.UUID) -> int:
    """How many people joined on this signup's link. Counted, never stored, so it can't drift."""
    return int(
        db.scalar(
            select(func.count())
            .select_from(WaitlistSignup)
            .where(WaitlistSignup.referred_by_id == signup_id)
        )
        or 0
    )


def _place(db: Session, signup: WaitlistSignup, *, is_new: bool) -> WaitlistPlace:
    ahead = int(
        db.scalar(
            select(func.count())
            .select_from(WaitlistSignup)
            .where(WaitlistSignup.created_at < signup.created_at)
        )
        or 0
    )
    total = int(db.scalar(select(func.count()).select_from(WaitlistSignup)) or 0)
    referrals = _referrals(db, signup.id)
    position = max(1, ahead + 1 - referrals * PLACES_PER_REFERRAL)
    return WaitlistPlace(
        position=position,
        referral_code=signup.referral_code,
        referrals=referrals,
        total=total,
        is_new=is_new,
    )


def join(
    db: Session,
    *,
    email: str,
    source: str | None = None,
    referral_code: str | None = None,
    ip_hash: str | None = None,
) -> WaitlistPlace:
    """Add an address to the list (or return the place it already has)."""
    address = normalize_email(email)

    existing = db.scalar(select(WaitlistSignup).where(WaitlistSignup.email == address))
    if existing is not None:
        return _place(db, existing, is_new=False)

    referrer: WaitlistSignup | None = None
    if referral_code:
        referrer = db.scalar(
            select(WaitlistSignup).where(WaitlistSignup.referral_code == referral_code.strip())
        )
        if referrer is not None and referrer.email == address:
            referrer = None  # no crediting yourself

    signup = WaitlistSignup(
        email=address,
        referral_code=_new_code(db),
        referred_by_id=referrer.id if referrer else None,
        source=(source or None),
        ip_hash=ip_hash,
    )
    db.add(signup)
    db.flush()
    db.refresh(signup)  # created_at is a server default
    return _place(db, signup, is_new=True)


def count(db: Session) -> int:
    """How many people are on the list."""
    return int(db.scalar(select(func.count()).select_from(WaitlistSignup)) or 0)


def export(db: Session, limit: int = 5000) -> list[WaitlistSignup]:
    """Every signup, oldest first. Owner-only — this is the one place addresses leave the DB."""
    return list(
        db.scalars(
            select(WaitlistSignup).order_by(WaitlistSignup.created_at.asc()).limit(limit)
        ).all()
    )


def remove(db: Session, email: str) -> bool:
    """Delete one signup by address. Returns whether a row was there to delete."""
    row = db.scalar(select(WaitlistSignup).where(WaitlistSignup.email == normalize_email(email)))
    if row is None:
        return False
    db.delete(row)
    return True
