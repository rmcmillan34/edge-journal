"""M8 Phase 1: Forex & Futures Support

Revision ID: 0019_forex_futures_support
Revises: 0018_saved_views
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0019_forex_futures_support'
down_revision = '0018_saved_views'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to instruments table
    op.add_column('instruments', sa.Column('pip_location', sa.Integer(), nullable=True))
    op.add_column('instruments', sa.Column('contract_size', sa.Integer(), nullable=True))
    op.add_column('instruments', sa.Column('tick_size', sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column('instruments', sa.Column('tick_value', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('instruments', sa.Column('expiration_date', sa.Date(), nullable=True))
    op.add_column('instruments', sa.Column('contract_month', sa.String(length=16), nullable=True))

    # Update asset_class to NOT NULL with default 'forex'
    # First set NULL values to 'forex'
    op.execute("UPDATE instruments SET asset_class = 'forex' WHERE asset_class IS NULL OR asset_class = ''")

    # Then alter column to NOT NULL with server default
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('instruments', schema=None) as batch_op:
        batch_op.alter_column('asset_class',
                             existing_type=sa.String(length=16),
                             nullable=False,
                             server_default='forex')

    # Set pip_location for existing instruments based on symbol
    op.execute("UPDATE instruments SET pip_location = 10 WHERE symbol LIKE '%JPY%'")
    op.execute("UPDATE instruments SET pip_location = 100 WHERE symbol LIKE '%XAU%' OR symbol LIKE '%XAG%' OR symbol LIKE '%GOLD%' OR symbol LIKE '%SILVER%'")
    op.execute("UPDATE instruments SET pip_location = 10000 WHERE pip_location IS NULL")

    # Add new columns to trades table
    # Forex-specific fields
    op.add_column('trades', sa.Column('lot_size', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('trades', sa.Column('pips', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('trades', sa.Column('swap', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('trades', sa.Column('stop_loss', sa.Numeric(precision=12, scale=6), nullable=True))
    op.add_column('trades', sa.Column('take_profit', sa.Numeric(precision=12, scale=6), nullable=True))

    # Futures-specific fields
    op.add_column('trades', sa.Column('contracts', sa.Integer(), nullable=True))
    op.add_column('trades', sa.Column('ticks', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade():
    # Remove columns from trades table
    op.drop_column('trades', 'ticks')
    op.drop_column('trades', 'contracts')
    op.drop_column('trades', 'take_profit')
    op.drop_column('trades', 'stop_loss')
    op.drop_column('trades', 'swap')
    op.drop_column('trades', 'pips')
    op.drop_column('trades', 'lot_size')

    # Revert asset_class to nullable
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('instruments', schema=None) as batch_op:
        batch_op.alter_column('asset_class',
                             existing_type=sa.String(length=16),
                             nullable=True,
                             server_default=None)

    # Remove columns from instruments table
    op.drop_column('instruments', 'contract_month')
    op.drop_column('instruments', 'expiration_date')
    op.drop_column('instruments', 'tick_value')
    op.drop_column('instruments', 'tick_size')
    op.drop_column('instruments', 'contract_size')
    op.drop_column('instruments', 'pip_location')
