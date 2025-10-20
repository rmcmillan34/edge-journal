"""daily journal models

Revision ID: 0008_daily_journal
Revises: 0007_trade_journal_attachments
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_daily_journal"
down_revision = "0007_trade_journal_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_journal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True, index=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("notes_md", sa.Text(), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "daily_journal_trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("daily_journal.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trade_id", sa.Integer(), sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.UniqueConstraint("journal_id", "trade_id", name="uq_daily_journal_trade"),
    )


def downgrade() -> None:
    op.drop_table("daily_journal_trades")
    op.drop_table("daily_journal")
