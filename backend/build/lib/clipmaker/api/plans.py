"""Public plan catalog (no authentication; used by the landing page)."""

from __future__ import annotations

from fastapi import APIRouter

from clipmaker.schemas import PlanOut
from clipmaker.services.billing import plan_catalog

router = APIRouter(tags=["plans"])


@router.get("/plans")
def list_plans() -> list[PlanOut]:
    """Plans with indicative prices and monthly credit allowances."""
    return plan_catalog()
