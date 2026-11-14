"""project share token

Revision ID: a1b2c3d4e5f6
Revises: c9587c5fa4f5
Create Date: 2026-11-14 08:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c9587c5fa4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("share_token", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_projects_share_token", "projects", ["share_token"])


def downgrade() -> None:
    op.drop_constraint("uq_projects_share_token", "projects", type_="unique")
    op.drop_column("projects", "share_token")
