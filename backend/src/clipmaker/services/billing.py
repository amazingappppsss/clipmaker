"""Plans and the credit ledger.

Credit unit: 1 credit = 1 minute of source video (rounded up). This keeps the user-facing
price tied to our dominant variable costs (transcription + analysis scale with duration).

Prices are in USD cents for the international launch, benchmarked against comparable tools
(Starter $15 / 150 min, Pro $29 / 300 min). Measured cost is ~$0.70 per source hour, so margins
are ~85%. TECH DEBT: revisit with real per-video cost data (Milestone 4); no unlimited plans.
Payment-provider integration is intentionally absent until the provider is chosen (M5).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from clipmaker.core.enums import Plan, UsageKind
from clipmaker.core.errors import InsufficientCreditsError
from clipmaker.db.models import UsageRecord, User
from clipmaker.schemas import PlanOut


@dataclass(frozen=True, slots=True)
class PlanSpec:
    """A plan's allowance and indicative price."""

    plan: Plan
    name: str
    monthly_credits: int
    price_usd_cents: int
    watermark: bool


PLANS: dict[Plan, PlanSpec] = {
    # Free is a one-time trial (15 minutes) to keep AI spend on non-paying users small.
    Plan.FREE: PlanSpec(Plan.FREE, "Free", monthly_credits=15, price_usd_cents=0, watermark=True),
    Plan.STARTER: PlanSpec(Plan.STARTER, "Starter", 150, price_usd_cents=1500, watermark=False),
    Plan.PRO: PlanSpec(Plan.PRO, "Pro", 300, price_usd_cents=2900, watermark=False),
}

SIGNUP_TRIAL_CREDITS = PLANS[Plan.FREE].monthly_credits


def credits_for_duration(duration_seconds: float) -> int:
    """Credits charged for processing a video of this length (min 1)."""
    return max(1, math.ceil(duration_seconds / 60))


def _record(
    db: Session,
    user: User,
    kind: UsageKind,
    credits: int,
    description: str,
    project_id: uuid.UUID | None = None,
    cost_usd: Decimal = Decimal(0),
) -> UsageRecord:
    rec = UsageRecord(
        user_id=user.id,
        project_id=project_id,
        kind=kind,
        credits=credits,
        description=description,
        cost_usd=cost_usd,
    )
    db.add(rec)
    user.credits_balance += credits
    return rec


def grant_credits(db: Session, user: User, credits: int, description: str) -> UsageRecord:
    """Add credits (signup trial, renewal)."""
    return _record(db, user, UsageKind.GRANT, credits, description)


def debit_credits(
    db: Session, user: User, credits: int, project_id: uuid.UUID, description: str
) -> UsageRecord:
    """Consume credits; the user row is locked to prevent concurrent double-spend.

    Raises:
        InsufficientCreditsError: when the balance is too low.
    """
    locked = db.execute(select(User).where(User.id == user.id).with_for_update()).scalar_one()
    if locked.credits_balance < credits:
        raise InsufficientCreditsError(
            f"This video needs {credits} credits but you have {locked.credits_balance}."
        )
    return _record(db, locked, UsageKind.DEBIT, -credits, description, project_id)


def refund_credits(
    db: Session, user: User, credits: int, project_id: uuid.UUID, description: str
) -> UsageRecord:
    """Return credits after a job fails for reasons that are not the user's fault."""
    return _record(db, user, UsageKind.REFUND, credits, description, project_id)


def ledger_balance(db: Session, user_id: uuid.UUID) -> int:
    """Recompute the balance from the ledger (source of truth; used for audits/tests)."""
    total = db.scalar(
        select(func.coalesce(func.sum(UsageRecord.credits), 0)).where(
            UsageRecord.user_id == user_id
        )
    )
    return int(total or 0)


def plan_catalog() -> list[PlanOut]:
    """Public plan list (served by GET /plans and inside GET /account/usage)."""
    return [
        PlanOut(
            plan=p.plan,
            name=p.name,
            monthly_credits=p.monthly_credits,
            price_usd_cents=p.price_usd_cents,
            watermark=p.watermark,
        )
        for p in PLANS.values()
    ]
