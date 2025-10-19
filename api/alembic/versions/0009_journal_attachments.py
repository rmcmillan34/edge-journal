"""add journal_id to attachments

Revision ID: 0009_journal_attachments
Revises: 0008_daily_journal
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_journal_attachments"
down_revision = "0008_daily_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("journal_id", sa.Integer(), nullable=True))
    # For SQLite compatibility, add index in a separate step
    op.create_index("ix_attachments_journal_id", "attachments", ["journal_id"], unique=False)
    # Add FK constraint if supported (SQLite will store it inline on table create; on alter it may be ignored)
    try:
        op.create_foreign_key(
            "fk_attachments_journal_id_daily_journal",
            "attachments",
            "daily_journal",
            ["journal_id"],
            ["id"],
            ondelete="CASCADE",
        )
    except Exception:
        # SQLite may not support adding FKs post-create; ignore in tests
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("fk_attachments_journal_id_daily_journal", "attachments", type_="foreignkey")
    except Exception:
        pass
    op.drop_index("ix_attachments_journal_id", table_name="attachments")
    op.drop_column("attachments", "journal_id")

