"""add turn timer fields turn_started_at, turn_expires_at

Revision ID: 20260204_timer
Revises: 20260129_cooldowns
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260204_timer"
down_revision: Union[str, Sequence[str], None] = "20260129_cooldowns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("turn_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "matches",
        sa.Column("turn_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "turn_expires_at")
    op.drop_column("matches", "turn_started_at")
