"""services/billing.py + services/users.py — credits ledger and trial grant."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from clipmaker.core.errors import InsufficientCreditsError
from clipmaker.core.security import AuthenticatedUser
from clipmaker.db.models import Project
from clipmaker.services.billing import (
    SIGNUP_TRIAL_CREDITS,
    credits_for_duration,
    debit_credits,
    ledger_balance,
    refund_credits,
)
from clipmaker.services.users import get_or_create_user


@pytest.mark.parametrize(("seconds", "credits"), [(1, 1), (60, 1), (61, 2), (1800, 30)])
def test_credits_for_duration(seconds: float, credits: int) -> None:
    assert credits_for_duration(seconds) == credits


def test_trial_granted_exactly_once(db: Session) -> None:
    identity = AuthenticatedUser(id=uuid.uuid4(), email="x@y.co")
    user = get_or_create_user(db, identity)
    get_or_create_user(db, identity)
    assert user.credits_balance == SIGNUP_TRIAL_CREDITS
    assert ledger_balance(db, user.id) == SIGNUP_TRIAL_CREDITS


def test_debit_refund_and_insufficient(db: Session) -> None:
    user = get_or_create_user(db, AuthenticatedUser(id=uuid.uuid4(), email=None))
    project = Project(user_id=user.id, title="p", settings={})
    db.add(project)
    db.commit()
    project_id = project.id
    debit_credits(db, user, 10, project_id, "test")
    db.commit()
    with pytest.raises(InsufficientCreditsError):
        debit_credits(db, user, SIGNUP_TRIAL_CREDITS, project_id, "too much")
    db.rollback()
    refund_credits(db, user, 10, project_id, "refund")
    db.commit()
    db.refresh(user)
    assert user.credits_balance == SIGNUP_TRIAL_CREDITS == ledger_balance(db, user.id)
