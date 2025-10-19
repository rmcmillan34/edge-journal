"""add sort_order to attachments

Revision ID: 0011_attachments_sort_order
Revises: 0010_attachments_trade_nullable
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_attachments_sort_order"
down_revision = "0010_attachments_trade_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    # remove server_default to avoid future implicit defaulting by DB
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.alter_column("sort_order", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.drop_column("sort_order")

