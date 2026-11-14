"""rename creator plan to starter

Revision ID: e09f68cbe898
Revises: 547ae01e5b28
Create Date: 2026-11-13 15:55:42.026146
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e09f68cbe898"
down_revision: str | None = "547ae01e5b28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Paid tiers are now Starter/Pro (international USD pricing). Rename keeps existing rows valid.
    op.execute("ALTER TYPE plan RENAME VALUE 'creator' TO 'starter'")


def downgrade() -> None:
    op.execute("ALTER TYPE plan RENAME VALUE 'starter' TO 'creator'")
