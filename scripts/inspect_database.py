"""Read-only demonstration evidence; never prints credentials or password hashes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.db.session import engine_for
if not settings.database_url:
    raise RuntimeError('Configure DATABASE_URL first')
with engine_for(settings.database_url).connect() as db:
    print('PostgreSQL:', db.scalar(text('SELECT version()')))
    print('Users (real database rows):')
    for row in db.execute(text("SELECT user_id, full_name, email, role, password_hash LIKE '$argon2id$%' AS argon2_hash FROM users ORDER BY user_id")):
        print(dict(row._mapping))
    print('Materials (internal paths excluded):')
    for row in db.execute(text('SELECT material_id, uploader_id, category_id, course_id, title, file_size_bytes FROM materials ORDER BY material_id')):
        print(dict(row._mapping))
