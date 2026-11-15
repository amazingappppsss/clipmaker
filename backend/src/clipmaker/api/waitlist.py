"""Public pre-launch waitlist (no authentication) plus an owner-only export.

This is the only endpoint the open internet can POST to without a token, so it is deliberately
narrow: one bounded body, a hidden field that only bots fill, a tight per-machine budget, and
a response that contains nothing about anyone but the caller.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from clipmaker.api.deps import AppSettings, CurrentUser, DbSession
from clipmaker.core.errors import NotFoundError, RateLimitedError
from clipmaker.core.rate_limit import Counter, get_counter, is_allowed
from clipmaker.schemas import (
    WaitlistEntryOut,
    WaitlistJoinIn,
    WaitlistPlaceOut,
    WaitlistStatsOut,
)
from clipmaker.services import waitlist

logger = logging.getLogger(__name__)
router = APIRouter(tags=["waitlist"])

HOUR = 3600


def client_ip(request: Request) -> str | None:
    """The caller's address.

    In production we sit behind the platform's proxy, which rewrites `x-forwarded-for`, so the
    first hop is the real client. A direct caller could spoof the header — which is why this
    only ever feeds a rate-limit bucket and a one-way hash, never an authorization decision.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


@router.get("/waitlist/stats", response_model=WaitlistStatsOut)
def waitlist_stats(db: DbSession) -> WaitlistStatsOut:
    """How many have joined and how many founding spots are left. Counters only."""
    total = waitlist.count(db)
    return WaitlistStatsOut(
        total=total,
        founding_spots=waitlist.FOUNDING_SPOTS,
        spots_left=max(0, waitlist.FOUNDING_SPOTS - total),
        places_per_referral=waitlist.PLACES_PER_REFERRAL,
    )


@router.post("/waitlist", response_model=WaitlistPlaceOut, status_code=201)
def join_waitlist(
    payload: WaitlistJoinIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
    counter: Annotated[Counter, Depends(get_counter)],
) -> WaitlistPlaceOut:
    """Join the waitlist, or get back the place you already hold."""
    ip = client_ip(request)
    if not is_allowed(counter, f"waitlist:{ip}", settings.waitlist_signups_per_hour, HOUR):
        raise RateLimitedError("Too many signups from here. Try again later.")

    if payload.company.strip():
        # A bot filled the hidden field. Answer like we would anyone else and write nothing,
        # so it has no signal to adapt to.
        logger.info("waitlist_honeypot")
        total = waitlist.count(db)
        return WaitlistPlaceOut(
            position=total + 1,
            referral_code="",
            referrals=0,
            total=total,
            places_per_referral=waitlist.PLACES_PER_REFERRAL,
        )

    place = waitlist.join(
        db,
        email=payload.email,
        source=payload.source,
        referral_code=payload.referral_code,
        ip_hash=waitlist.hash_ip(ip, settings.storage_signing_key.get_secret_value()),
    )
    db.commit()
    # Never log the address itself.
    logger.info("waitlist_join", extra={"new": place.is_new, "position": place.position})
    return WaitlistPlaceOut(
        position=place.position,
        referral_code=place.referral_code,
        referrals=place.referrals,
        total=place.total,
        places_per_referral=waitlist.PLACES_PER_REFERRAL,
    )


@router.get("/waitlist/export", response_model=list[WaitlistEntryOut])
def export_waitlist(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> list[WaitlistEntryOut]:
    """Every signup, for the owner only.

    Anyone else gets a 404 rather than a 403, so the endpoint doesn't advertise that it exists.
    """
    if (user.email or "").lower() not in settings.owner_email_set:
        raise NotFoundError("Not found")
    rows = waitlist.export(db)
    counts = {row.id: 0 for row in rows}
    for row in rows:
        if row.referred_by_id in counts:
            counts[row.referred_by_id] += 1
    return [
        WaitlistEntryOut(
            email=row.email,
            referral_code=row.referral_code,
            referrals=counts.get(row.id, 0),
            source=row.source,
            created_at=row.created_at,
        )
        for row in rows
    ]
