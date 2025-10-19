"""user scope on accounts & uploads

Revision ID: 0005_user_scope_accounts_uploads
Revises: 0004_uploads_summary
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_user_scope_accounts_uploads"
down_revision = "0004_uploads_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"]) 
    # ForeignKey could be added via batch operations; skipped for SQLite simplicity

    op.add_column("uploads", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"]) 


def downgrade() -> None:
    op.drop_index("ix_uploads_user_id", table_name="uploads")
    op.drop_column("uploads", "user_id")
    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_column("accounts", "user_id")

