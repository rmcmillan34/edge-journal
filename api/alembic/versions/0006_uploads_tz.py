"""add tz column to uploads

Revision ID: 0006_uploads_tz
Revises: 0005_user_scope_accounts_uploads
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_uploads_tz"
down_revision = "0005_user_scope_accounts_uploads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploads", sa.Column("tz", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("uploads", "tz")

