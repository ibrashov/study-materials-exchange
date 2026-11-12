"""Week 11 (Daryn): trigram search indexes and composite list indexes."""
from alembic import op
import sqlalchemy as sa
revision = '0003_search_indexes'
down_revision = '0002_admin_reports'
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.create_index('ix_materials_title_trgm', 'materials', ['title'], postgresql_using='gin',
                    postgresql_ops={'title': 'gin_trgm_ops'})
    op.create_index('ix_courses_name_trgm', 'courses', ['course_name'], postgresql_using='gin',
                    postgresql_ops={'course_name': 'gin_trgm_ops'})
    op.create_index('ix_categories_name_trgm', 'categories', ['category_name'], postgresql_using='gin',
                    postgresql_ops={'category_name': 'gin_trgm_ops'})
    op.create_index('ix_materials_course_newest', 'materials', ['course_id', sa.text('material_id DESC')])
    op.create_index('ix_materials_category_newest', 'materials', ['category_id', sa.text('material_id DESC')])
    # The composite indexes replace the single-column ones (leftmost-prefix covers them).
    op.drop_index('ix_materials_course_id', 'materials')
    op.drop_index('ix_materials_category_id', 'materials')

def downgrade():
    op.create_index('ix_materials_category_id', 'materials', ['category_id'])
    op.create_index('ix_materials_course_id', 'materials', ['course_id'])
    for name, table in (('ix_materials_category_newest', 'materials'), ('ix_materials_course_newest', 'materials'),
                        ('ix_categories_name_trgm', 'categories'), ('ix_courses_name_trgm', 'courses'),
                        ('ix_materials_title_trgm', 'materials')):
        op.drop_index(name, table)
