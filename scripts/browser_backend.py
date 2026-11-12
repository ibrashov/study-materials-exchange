"""Dedicated test-only HTTP server. Refuses the development database."""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from backend.app.core.config import ROOT, settings
from backend.app.db.seed import main as seed
import uvicorn

url = settings.test_database_url
if not url or not (make_url(url).database or '').endswith('_test') or make_url(url) == make_url(settings.database_url):
    raise RuntimeError('A separate TEST_DATABASE_URL ending in _test is required')
settings.database_url = url
settings.rate_limit_enabled = False  # browser suites register many accounts from one IP; limits are covered by tests/test_week11.py
settings.uploads_dir = ROOT / '.local-postgres' / 'browser-uploads'
os.chdir(ROOT)
command.upgrade(Config('alembic.ini'), 'head')
seed()
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.db.session import engine_for
from backend.app.models.entities import User
from backend.app.services.auth import hasher
with Session(engine_for(url)) as db:
    email = 'browser-admin@example.com'
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(full_name='Browser Test Admin', email=email, role='admin')
        db.add(user)
    user.password_hash = hasher.hash(os.environ['BROWSER_TEST_ADMIN_PASSWORD'])
    db.commit()
uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8001)
