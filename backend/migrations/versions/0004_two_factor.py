"""Week 11 (Arnur): TOTP two-factor columns."""
from alembic import op
import sqlalchemy as sa
revision = '0004_two_factor'
down_revision = '0003_search_indexes'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('totp_secret', sa.Text()))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
