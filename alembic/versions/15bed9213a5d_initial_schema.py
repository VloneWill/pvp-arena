"""initial schema

Revision ID: 15bed9213a5d
Revises:
Create Date: 2026-01-29 14:51:15.120586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "15bed9213a5d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create users and matches tables."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("class_name", sa.String(20), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player1_id", sa.Integer(), nullable=False),
        sa.Column("player2_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("player1_health", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("player2_health", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("current_turn", sa.Integer(), nullable=True),
        sa.Column("turn_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("player1_defending", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("player2_defending", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("player1_ability_effect", sa.String(50), nullable=True),
        sa.Column("player2_ability_effect", sa.String(50), nullable=True),
        sa.Column("player1_ability_cooldown", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("player2_ability_cooldown", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("xp_awarded", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("combat_log", sa.JSON(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["current_turn"], ["users.id"]),
        sa.ForeignKeyConstraint(["player1_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["player2_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["winner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_matches_id", "matches", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop matches and users."""
    op.drop_index("ix_matches_id", table_name="matches")
    op.drop_table("matches")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
