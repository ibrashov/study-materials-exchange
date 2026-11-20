"""Trash soft-delete columns, gamification tables, and persistent app settings."""
from alembic import op
import sqlalchemy as sa

revision = '0005_trash_gamification'
down_revision = '0004_two_factor'
branch_labels = None
depends_on = None


def upgrade():
    # Trash (soft-delete) on materials
    op.add_column('materials', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('materials', sa.Column('deleted_by_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=True))
    op.create_index('ix_materials_deleted_at', 'materials', ['deleted_at'])

    # Gamification fields on users
    op.add_column('users', sa.Column('xp_points', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('users', sa.Column('current_streak', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('users', sa.Column('longest_streak', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('users', sa.Column('last_activity_date', sa.Date(), nullable=True))

    # Gamification XP history
    op.create_table(
        'xp_events',
        sa.Column('event_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_xp_events_user_id', 'xp_events', ['user_id'])

    # Gamification badges
    op.create_table(
        'user_badges',
        sa.Column('badge_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('badge_code', sa.String(50), nullable=False),
        sa.Column('earned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'badge_code', name='uq_user_badges_user_code'),
    )
    op.create_index('ix_user_badges_user_id', 'user_badges', ['user_id'])

    # Persistent key-value settings (scheduled backup config & AI agent config)
    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('value_json', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('app_settings')

    op.drop_index('ix_user_badges_user_id', table_name='user_badges')
    op.drop_table('user_badges')

    op.drop_index('ix_xp_events_user_id', table_name='xp_events')
    op.drop_table('xp_events')

    op.drop_column('users', 'last_activity_date')
    op.drop_column('users', 'longest_streak')
    op.drop_column('users', 'current_streak')
    op.drop_column('users', 'xp_points')

    op.drop_index('ix_materials_deleted_at', table_name='materials')
    op.drop_column('materials', 'deleted_by_id')
    op.drop_column('materials', 'deleted_at')
