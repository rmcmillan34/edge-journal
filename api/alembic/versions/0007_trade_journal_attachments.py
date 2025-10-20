"""add trade journal fields and attachments table

Revision ID: 0007_trade_journal_attachments
Revises: 0006_uploads_tz
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_trade_journal_attachments"
down_revision = "0006_uploads_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres requires boolean defaults as true/false, not 1/0
    op.add_column("trades", sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("trades", sa.Column("post_analysis_md", sa.Text(), nullable=True))

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trade_id", sa.Integer(), sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("thumb_path", sa.String(512), nullable=True),
        sa.Column("timeframe", sa.String(8), nullable=True),
        sa.Column("state", sa.String(16), nullable=True),
        sa.Column("view", sa.String(24), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_column("trades", "post_analysis_md")
    op.drop_column("trades", "reviewed")
