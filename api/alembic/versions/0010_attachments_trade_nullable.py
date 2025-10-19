"""make attachments.trade_id nullable for journal attachments

Revision ID: 0010_attachments_trade_nullable
Revises: 0009_journal_attachments
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_attachments_trade_nullable"
down_revision = "0009_journal_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.alter_column("trade_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.alter_column("trade_id", existing_type=sa.Integer(), nullable=False)

