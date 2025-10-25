"""M6: add breach acknowledgements and enforcement_mode

Revision ID: 0016_m6_breach_ack_enforce
Revises: 0015_accounts_risk_cap
Create Date: 2025-10-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0016_m6_breach_ack_enforce'
down_revision = '0015_accounts_risk_cap'
branch_labels = None
depends_on = None


def upgrade():
    # user_trading_rules: enforcement_mode
    with op.batch_alter_table('user_trading_rules') as batch_op:
        batch_op.add_column(sa.Column('enforcement_mode', sa.String(length=8), nullable=False, server_default='off'))
    op.execute("UPDATE user_trading_rules SET enforcement_mode = 'off' WHERE enforcement_mode IS NULL")
    with op.batch_alter_table('user_trading_rules') as batch_op:
        batch_op.alter_column('enforcement_mode', server_default=None)

    # breach_events: acknowledgements
    with op.batch_alter_table('breach_events') as batch_op:
        batch_op.add_column(sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('acknowledged_by', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('breach_events') as batch_op:
        batch_op.drop_column('acknowledged_by')
        batch_op.drop_column('acknowledged_at')
        batch_op.drop_column('acknowledged')
    with op.batch_alter_table('user_trading_rules') as batch_op:
        batch_op.drop_column('enforcement_mode')

