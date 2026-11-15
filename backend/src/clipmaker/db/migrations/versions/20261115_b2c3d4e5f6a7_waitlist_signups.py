"""waitlist signups

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-15 05:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waitlist_signups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("referral_code", sa.String(length=16), nullable=False),
        sa.Column(
            "referred_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("waitlist_signups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email", name="uq_waitlist_signups_email"),
        sa.UniqueConstraint("referral_code", name="uq_waitlist_signups_referral_code"),
    )
    op.create_index("ix_waitlist_created", "waitlist_signups", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_waitlist_created", table_name="waitlist_signups")
    op.drop_table("waitlist_signups")
