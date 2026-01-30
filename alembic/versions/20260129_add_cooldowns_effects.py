"""add cooldowns and effects columns for multi-ability system

Revision ID: 20260129_cooldowns
Revises: 15bed9213a5d
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260129_cooldowns"
down_revision: Union[str, Sequence[str], None] = "15bed9213a5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("player1_cooldowns", sa.JSON(), nullable=True))
    op.add_column("matches", sa.Column("player2_cooldowns", sa.JSON(), nullable=True))
    op.add_column("matches", sa.Column("player1_effects", sa.JSON(), nullable=True))
    op.add_column("matches", sa.Column("player2_effects", sa.JSON(), nullable=True))
    # Backfill existing rows (app treats None as {} or [])
    op.execute(sa.text("UPDATE matches SET player1_cooldowns = '{}' WHERE player1_cooldowns IS NULL"))
    op.execute(sa.text("UPDATE matches SET player2_cooldowns = '{}' WHERE player2_cooldowns IS NULL"))
    op.execute(sa.text("UPDATE matches SET player1_effects = '[]' WHERE player1_effects IS NULL"))
    op.execute(sa.text("UPDATE matches SET player2_effects = '[]' WHERE player2_effects IS NULL"))


def downgrade() -> None:
    op.drop_column("matches", "player2_effects")
    op.drop_column("matches", "player1_effects")
    op.drop_column("matches", "player2_cooldowns")
    op.drop_column("matches", "player1_cooldowns")
