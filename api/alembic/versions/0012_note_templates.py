"""note templates

Revision ID: 0012_note_templates
Revises: 0011_attachments_sort_order
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0012_note_templates"
down_revision = "0011_attachments_sort_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "note_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("target", sa.String(16), nullable=False),
        sa.Column("sections_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name", "target", name="uq_note_templates_user_name_target"),
    )


def downgrade() -> None:
    op.drop_table("note_templates")

