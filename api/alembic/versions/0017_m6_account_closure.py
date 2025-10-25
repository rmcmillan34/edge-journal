"""M6: add account closure tracking fields

Revision ID: 0017_m6_account_closure
Revises: 0016_m6_breach_ack_enforce
Create Date: 2025-10-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0017_m6_account_closure'
down_revision = '0016_m6_breach_ack_enforce'
branch_labels = None
depends_on = None


def upgrade():
    # accounts: closure tracking
    with op.batch_alter_table('accounts') as batch_op:
        batch_op.add_column(sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('close_reason', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('close_note', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('accounts') as batch_op:
        batch_op.drop_column('close_note')
        batch_op.drop_column('close_reason')
        batch_op.drop_column('closed_at')
