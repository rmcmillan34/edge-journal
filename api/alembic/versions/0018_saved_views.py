"""M7 Phase 2: Saved Views

Revision ID: 0018_saved_views
Revises: 0017_m6_account_closure
Create Date: 2025-10-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0018_saved_views'
down_revision = '0017_m6_account_closure'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filters_json', sa.Text(), nullable=False),
        sa.Column('columns_json', sa.Text(), nullable=True),
        sa.Column('sort_json', sa.Text(), nullable=True),
        sa.Column('group_by', sa.String(length=64), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'name', name='unique_user_view_name')
    )
    op.create_index('idx_saved_views_user', 'saved_views', ['user_id'])
    op.create_index('idx_saved_views_default', 'saved_views', ['user_id', 'is_default'])


def downgrade():
    op.drop_index('idx_saved_views_default')
    op.drop_index('idx_saved_views_user')
    op.drop_table('saved_views')
