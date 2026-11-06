"""Account blocking and download statistics for the admin panel."""
from alembic import op
import sqlalchemy as sa
revision = '0002_admin_reports'
down_revision = '0001_week10'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('materials', sa.Column('download_count', sa.Integer(), nullable=False, server_default=sa.text('0')))

def downgrade():
    op.drop_column('materials', 'download_count')
    op.drop_column('users', 'is_active')
