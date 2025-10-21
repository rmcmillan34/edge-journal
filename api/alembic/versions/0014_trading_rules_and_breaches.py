"""trading rules and breach events

Revision ID: 0014_trading_rules_and_breaches
Revises: 0013_playbooks_core
Create Date: 2025-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_trading_rules_and_breaches"
down_revision = "0013_playbooks_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_trading_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("max_losses_row_day", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("max_losing_days_streak_week", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_losing_weeks_streak_month", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "breach_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("date_or_week", sa.String(16), nullable=False),
        sa.Column("rule_key", sa.String(48), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_breach_events_user_date", "breach_events", ["user_id", "date_or_week"])


def downgrade() -> None:
    op.drop_index("ix_breach_events_user_date", table_name="breach_events")
    op.drop_table("breach_events")
    op.drop_table("user_trading_rules")

