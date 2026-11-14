"""User provisioning: mirror Supabase identities into the local `users` table."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from clipmaker.core.security import AuthenticatedUser
from clipmaker.db.models import User
from clipmaker.services.billing import SIGNUP_TRIAL_CREDITS, grant_credits


def top_up_owner(db: Session, user: User, owner_emails: frozenset[str], floor: int) -> None:
    """Keep owner/tester accounts at `floor` credits (recorded as a normal grant)."""
    if not user.email or user.email.lower() not in owner_emails:
        return
    if user.credits_balance < floor:
        grant_credits(db, user, floor - user.credits_balance, "Owner test credits")
        db.commit()


def get_or_create_user(db: Session, identity: AuthenticatedUser) -> User:
    """Return the local user, creating it (with trial credits) on first sight.

    Uses INSERT ... ON CONFLICT DO NOTHING so concurrent first requests cannot create
    duplicates or grant the trial twice.
    """
    existing = db.get(User, identity.id)
    if existing is not None:
        if identity.email and existing.email != identity.email:
            existing.email = identity.email
            db.commit()
        return existing

    # RETURNING yields a row only if *this* statement inserted it (rowcount is unreliable here).
    inserted_id = db.execute(
        insert(User)
        .values(id=identity.id, email=identity.email, credits_balance=0)
        .on_conflict_do_nothing(index_elements=[User.id])
        .returning(User.id)
    ).scalar_one_or_none()
    user = db.get(User, identity.id)
    assert user is not None
    if inserted_id is not None:  # we won the race: grant the trial exactly once
        grant_credits(db, user, SIGNUP_TRIAL_CREDITS, "Free trial credits")
    db.commit()
    return user
