"""uploads summary columns

Revision ID: 0004_uploads_summary
Revises: 0003_mapping_presets
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_uploads_summary"
down_revision = "0003_mapping_presets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploads", sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("uploads", sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("uploads", sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("uploads", sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("uploads", sa.Column("errors_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("uploads", "errors_json")
    op.drop_column("uploads", "error_count")
    op.drop_column("uploads", "skipped_count")
    op.drop_column("uploads", "updated_count")
    op.drop_column("uploads", "inserted_count")

