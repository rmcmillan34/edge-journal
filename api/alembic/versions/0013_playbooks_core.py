"""playbooks core tables

Revision ID: 0013_playbooks_core
Revises: 0012_note_templates
Create Date: 2025-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_playbooks_core"
down_revision = "0012_note_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playbook_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("strategy_bindings_json", sa.Text(), nullable=True),
        sa.Column("schema_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("grade_scale", sa.String(16), nullable=False, server_default="A_B_C_D"),
        sa.Column("grade_thresholds_json", sa.Text(), nullable=True),
        sa.Column("risk_schedule_json", sa.Text(), nullable=True),
        sa.Column("template_max_risk_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name", "version", name="uq_playbook_templates_user_name_version"),
    )

    op.create_table(
        "playbook_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("trade_id", sa.Integer(), sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("daily_journal.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("playbook_templates.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("values_json", sa.Text(), nullable=False),
        sa.Column("comments_json", sa.Text(), nullable=True),
        sa.Column("computed_grade", sa.String(1), nullable=True),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("intended_risk_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_playbook_responses_template", "playbook_responses", ["template_id", "template_version"])
    op.create_index("ix_playbook_responses_trade", "playbook_responses", ["trade_id"])

    op.create_table(
        "playbook_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("response_id", sa.Integer(), sa.ForeignKey("playbook_responses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_playbook_evidence_response", "playbook_evidence_links", ["response_id"])


def downgrade() -> None:
    op.drop_index("ix_playbook_evidence_response", table_name="playbook_evidence_links")
    op.drop_table("playbook_evidence_links")
    op.drop_index("ix_playbook_responses_trade", table_name="playbook_responses")
    op.drop_index("ix_playbook_responses_template", table_name="playbook_responses")
    op.drop_table("playbook_responses")
    op.drop_table("playbook_templates")

