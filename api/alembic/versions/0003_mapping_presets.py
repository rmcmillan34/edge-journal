"""mapping presets table

Revision ID: 0003_mapping_presets
Revises: 0002_core_tables
Create Date: 2025-10-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_mapping_presets"
down_revision = "0002_core_tables"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "mapping_presets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("headers_json", sa.Text, nullable=False),   # JSON string (list of headers as seen)
        sa.Column("mapping_json", sa.Text, nullable=False),   # JSON string ({Canonical: CSVHeader})
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_mapping_presets_user_name"),
    )

def downgrade() -> None:
    op.drop_table("mapping_presets")
