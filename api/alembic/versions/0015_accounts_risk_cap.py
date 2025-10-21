"""accounts risk cap column

Revision ID: 0015_accounts_risk_cap
Revises: 0014_trading_rules_and_breaches
Create Date: 2025-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0015_accounts_risk_cap"
down_revision = "0014_trading_rules_and_breaches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("account_max_risk_pct", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "account_max_risk_pct")

