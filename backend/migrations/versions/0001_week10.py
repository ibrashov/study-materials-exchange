"""Initial PostgreSQL schema; historical SQLite is unchanged."""
from alembic import op
import sqlalchemy as sa
revision = '0001_week10'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users', sa.Column('user_id', sa.Integer(), primary_key=True),
        sa.Column('full_name', sa.String(120), nullable=False), sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('password_hash', sa.Text(), nullable=False), sa.Column('role', sa.String(10), nullable=False),
        sa.CheckConstraint("role IN ('student', 'admin')", name='ck_users_role'))
    op.create_table('categories', sa.Column('category_id', sa.Integer(), primary_key=True),
        sa.Column('category_name', sa.String(100), nullable=False, unique=True), sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('courses', sa.Column('course_id', sa.Integer(), primary_key=True),
        sa.Column('course_name', sa.String(150), nullable=False), sa.Column('course_code', sa.String(30), nullable=False, unique=True),
        sa.Column('description', sa.Text()))
    op.create_table('materials', sa.Column('material_id', sa.Integer(), primary_key=True),
        sa.Column('uploader_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.category_id'), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.course_id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False), sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(btrim(title, E' \t\n\r')) > 0", name='ck_materials_title'),
        sa.CheckConstraint('file_size_bytes BETWEEN 1 AND 52428800', name='ck_materials_size'))
    for field in ('uploader_id', 'category_id', 'course_id'):
        op.create_index('ix_materials_' + field, 'materials', [field])

def downgrade():
    for table in ('materials', 'courses', 'categories', 'users'):
        op.drop_table(table)
