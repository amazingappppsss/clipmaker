"""Account endpoints: plan, credits, usage history."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from clipmaker.api.deps import CurrentUser, DbSession
from clipmaker.db.models import UsageRecord
from clipmaker.schemas import AccountUsage, UsageRecordOut
from clipmaker.services.billing import plan_catalog

router = APIRouter(prefix="/account", tags=["account"])

HISTORY_LIMIT = 100


@router.get("/usage")
def get_usage(user: CurrentUser, db: DbSession) -> AccountUsage:
    """Current plan, credit balance, recent ledger entries and the plan catalog."""
    history = db.scalars(
        select(UsageRecord)
        .where(UsageRecord.user_id == user.id)
        .order_by(UsageRecord.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    return AccountUsage(
        email=user.email,
        plan=user.plan,
        credits_balance=user.credits_balance,
        history=[UsageRecordOut.model_validate(r) for r in history],
        plans=plan_catalog(),
    )
