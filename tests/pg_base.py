"""Shared setup for real PostgreSQL API tests. Uses only the _test database."""
import io
from pathlib import Path
import tempfile
import unittest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.session import engine_for, get_db
from backend.app.main import app
from backend.app.models.entities import Category, Course, User
from backend.app.services.auth import create_token, hasher
from backend.app.services.rate_limit import reset_all

PASSWORD = 'Test-password-123!'

def pdf_bytes(password=None):
    target = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    if password:
        writer.encrypt(password)
    writer.write(target)
    return target.getvalue()

class PostgresCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = settings.test_database_url
        if not url:
            raise unittest.SkipTest('TEST_DATABASE_URL not configured; PostgreSQL tests NOT RUN')
        parsed = make_url(url)
        if parsed.drivername != 'postgresql+psycopg' or not (parsed.database or '').endswith('_test'):
            raise RuntimeError('Refusing non-PostgreSQL or non-_test database')
        cls.url = url
        cls.engine = engine_for(url)
        original = settings.database_url
        try:
            settings.database_url = url
            command.upgrade(Config('alembic.ini'), 'head')
        finally:
            settings.database_url = original
        cls.password_hash = hasher.hash(PASSWORD)

    def setUp(self):
        with self.engine.begin() as connection:
            connection.execute(text('TRUNCATE materials, users, categories, courses RESTART IDENTITY CASCADE'))
        self.temp = tempfile.TemporaryDirectory()
        self.previous = settings.uploads_dir, settings.auth_secret
        settings.uploads_dir = Path(self.temp.name)
        settings.auth_secret = 'test-only-secret-that-is-long-enough-12345'
        def test_db():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = test_db
        reset_all()
        self.client = TestClient(app)
        with Session(self.engine) as db:
            db.add_all([Category(category_name='Lecture Notes'), Course(course_code='PROG101', course_name='Programming'),
                        Course(course_code='DB101', course_name='Database Systems'),
                        User(full_name='Test Admin', email='admin@example.com', password_hash=self.password_hash, role='admin'),
                        User(full_name='Student One', email='one@example.com', password_hash=self.password_hash, role='student'),
                        User(full_name='Student Two', email='two@example.com', password_hash=self.password_hash, role='student')])
            db.commit()
        self.addCleanup(self.temp.cleanup)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        settings.uploads_dir, settings.auth_secret = self.previous

    def auth(self, user_id):
        return {'Authorization': 'Bearer ' + create_token(user_id)}

    @property
    def admin(self): return self.auth(1)
    @property
    def one(self): return self.auth(2)
    @property
    def two(self): return self.auth(3)

    def upload(self, headers=None, title='Notes', body=None, course_id=1):
        return self.client.post('/api/materials', headers=headers or self.one,
                                data={'title': title, 'category_id': 1, 'course_id': course_id},
                                files={'file': ('notes.pdf', body if body is not None else pdf_bytes(), 'application/pdf')})

    def stored_files(self):
        return sorted(path.name for path in settings.uploads_dir.iterdir())
