"""Real PostgreSQL integration tests. No SQLite substitution."""
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import jwt
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, text, func
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pypdf import PdfWriter
from backend.app.core.config import settings, MAX_FILE_BYTES
from backend.app.db.session import engine_for, get_db
from backend.app.main import app
from backend.app.models.entities import User, Material, Category, Course
from backend.app.services.auth import hasher, create_token
from backend.app.services.storage import save_pdf
from starlette.datastructures import UploadFile

PASSWORD = 'Test-password-123!'

def pdf_bytes():
    target = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(target)
    return target.getvalue()

class PostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = settings.test_database_url
        if not url:
            raise unittest.SkipTest('TEST_DATABASE_URL not configured; PostgreSQL tests NOT RUN')
        parsed = make_url(url)
        if parsed.drivername != 'postgresql+psycopg' or not (parsed.database or '').endswith('_test'):
            raise RuntimeError('Refusing non-PostgreSQL or non-_test database')
        if settings.database_url and parsed == make_url(settings.database_url):
            raise RuntimeError('Test database must differ from development database')
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
        self.previous_uploads = settings.uploads_dir
        self.previous_secret = settings.auth_secret
        settings.uploads_dir = Path(self.temp.name)
        settings.auth_secret = 'test-only-secret-that-is-long-enough-12345'
        def test_db():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        with Session(self.engine) as db:
            db.add_all([Category(category_name='Lecture Notes'), Course(course_code='PROG101', course_name='Programming'),
                        User(full_name='Test Admin', email='admin@example.com', password_hash=self.password_hash, role='admin')])
            db.commit()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        settings.uploads_dir = self.previous_uploads
        settings.auth_secret = self.previous_secret
        self.temp.cleanup()

    def register(self, **changes):
        body = {'full_name': ' Example Student ', 'email': 'student@example.com', 'password': PASSWORD}
        body.update(changes)
        return self.client.post('/api/auth/register', json=body)

    def login(self, email='student@example.com'):
        response = self.client.post('/api/auth/login', json={'email': email, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return {'Authorization': 'Bearer ' + response.json()['access_token']}

    def upload(self, content=None, **fields):
        data = {'title': 'Programming notes', 'category_id': '1', 'course_id': '1'}
        data.update(fields)
        return self.client.post('/api/materials', headers=self.login(), data=data,
                                files={'file': ('../../notes.pdf', pdf_bytes() if content is None else content, 'application/pdf')})

    def test_registration_persists_and_hashes(self):
        response = self.register(email=' Student@EXAMPLE.com ')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), {'user_id', 'full_name', 'email', 'role'})
        self.assertEqual(response.json()['email'], 'student@example.com')
        self.assertEqual(response.json()['full_name'], 'Example Student')
        with Session(self.engine) as db:
            user = db.get(User, response.json()['user_id'])
            self.assertEqual(user.role, 'student')
            self.assertTrue(user.password_hash.startswith('$argon2id$'))
            self.assertTrue(hasher.verify(user.password_hash, PASSWORD))

    def test_missing_fields(self):
        self.assertEqual(self.client.post('/api/auth/register', json={}).status_code, 422)

    def test_duplicate_normalized_email(self):
        self.register()
        self.assertEqual(self.register(email='STUDENT@example.com').status_code, 409)

    def test_invalid_email(self):
        self.assertEqual(self.register(email='not-email').status_code, 422)

    def test_role_injection_and_password_policy(self):
        for body in ({'role': 'admin'}, {'password': 'short'}, {'full_name': '  '}):
            self.assertEqual(self.register(**body).status_code, 422)

    def test_student_forbidden_admin(self):
        self.register()
        self.assertEqual(self.client.get('/api/admin/overview', headers=self.login()).status_code, 403)

    def test_admin_real_counts(self):
        self.register()
        response = self.client.get('/api/admin/overview', headers=self.login('admin@example.com'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'total_users': 2, 'total_materials': 0})

    def test_guest_admin_and_upload_denied(self):
        self.assertEqual(self.client.get('/api/admin/overview').status_code, 401)
        self.assertEqual(self.client.post('/api/materials', data={'title': 'X', 'category_id': 1, 'course_id': 1},
                                        files={'file': ('a.pdf', pdf_bytes())}).status_code, 401)

    def test_invalid_expired_and_forged_tokens(self):
        now = datetime.now(timezone.utc)
        expired = jwt.encode({'sub': '1', 'iat': now - timedelta(hours=2), 'exp': now - timedelta(hours=1),
                              'iss': 'study-materials-backend', 'aud': 'study-materials'}, settings.auth_secret, algorithm='HS256')
        for token in ('invalid', expired, create_token(99999)):
            self.assertEqual(self.client.get('/api/admin/overview', headers={'Authorization': 'Bearer ' + token}).status_code, 401)
        forged = jwt.encode({'sub': '1', 'iat': now, 'exp': now + timedelta(hours=1),
                              'iss': 'study-materials-backend', 'aud': 'study-materials'}, 'wrong-secret-long-enough-for-hmac-test', algorithm='HS256')
        self.assertEqual(self.client.get('/api/admin/overview', headers={'Authorization': 'Bearer ' + forged}).status_code, 401)

    def test_login_wrong_password(self):
        self.register()
        response = self.client.post('/api/auth/login', json={'email': 'student@example.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)

    def test_database_role_rechecked(self):
        headers = self.login('admin@example.com')
        with Session(self.engine) as db:
            db.get(User, 1).role = 'student'
            db.commit()
        self.assertEqual(self.client.get('/api/admin/overview', headers=headers).status_code, 403)

    def test_pdf_upload_search_download(self):
        self.register()
        content = pdf_bytes()
        response = self.upload(content, uploader_id='1')
        self.assertEqual(response.status_code, 201, response.text)
        material = response.json()
        self.assertNotIn('file_path', material)
        self.assertEqual(material['uploader_id'], 2)
        self.assertEqual(material['file_size_bytes'], len(content))
        with Session(self.engine) as db:
            row = db.get(Material, material['material_id'])
            self.assertEqual((settings.uploads_dir / row.file_path).read_bytes(), content)
            self.assertNotIn('..', row.file_path)
        for query in ('programming', 'lecture', 'notes'):
            self.assertEqual(self.client.get('/api/materials', params={'q': query}).json()['total'], 1)
        self.assertEqual(self.client.get('/api/materials?q=absent').json()['items'], [])
        self.assertEqual(self.client.get('/api/materials?course_id=999').json()['total'], 0)
        route = f"/api/materials/{material['material_id']}/download"
        self.assertEqual(self.client.get(route).status_code, 401)
        downloaded = self.client.get(route, headers=self.login())
        self.assertEqual(downloaded.content, content)
        self.assertIn('attachment', downloaded.headers['content-disposition'])

    def test_invalid_pdf_empty_and_references_cleanup(self):
        self.register()
        for content, expected in ((b'', 422), (b'not pdf', 415), (b'%PDF-1.7 fake', 415)):
            self.assertEqual(self.upload(content).status_code, expected)
        for fields in ({'category_id': '999'}, {'course_id': '999'}, {'title': '   '}):
            self.assertEqual(self.upload(**fields).status_code, 422)
        self.assertEqual(list(settings.uploads_dir.iterdir()), [])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Material)), 0)

    def test_oversized_actual_bytes(self):
        self.register()
        self.assertEqual(self.upload(b'%PDF-' + b'x' * (MAX_FILE_BYTES - 4)).status_code, 413)
        self.assertEqual(list(settings.uploads_dir.iterdir()), [])

    def test_exact_storage_byte_boundary(self):
        # Isolates counting from parser validation; PDF parser is NOT exercised here.
        with tempfile.TemporaryFile() as source:
            source.truncate(MAX_FILE_BYTES)
            source.seek(0)
            with patch('backend.app.services.storage.validate_pdf') as validation:
                name, size = save_pdf(UploadFile(source, filename='boundary.pdf'))
                validation.assert_called_once()
            self.assertEqual(size, MAX_FILE_BYTES)
            self.assertEqual((settings.uploads_dir / name).stat().st_size, MAX_FILE_BYTES)

    def test_database_failure_removes_saved_file(self):
        self.register()
        with patch.object(Session, 'commit', side_effect=IntegrityError('test', {}, Exception('simulated failure'))):
            response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(list(settings.uploads_dir.iterdir()), [])

    def test_admin_cannot_upload(self):
        response = self.client.post('/api/materials', headers=self.login('admin@example.com'),
                                    data={'title': 'Notes', 'category_id': 1, 'course_id': 1}, files={'file': ('a.pdf', pdf_bytes())})
        self.assertEqual(response.status_code, 403)

    def test_postgres_keys_and_constraints(self):
        base = {'uploader_id': 1, 'category_id': 1, 'course_id': 1, 'title': 'Notes', 'file_path': 'test.pdf', 'file_size_bytes': 1}
        for field in ('uploader_id', 'category_id', 'course_id'):
            with Session(self.engine) as db, self.assertRaises(IntegrityError):
                db.add(Material(**(base | {field: 999})))
                db.commit()
        for size in (0, MAX_FILE_BYTES + 1):
            with Session(self.engine) as db, self.assertRaises(IntegrityError):
                db.add(Material(**(base | {'file_size_bytes': size})))
                db.commit()
        with Session(self.engine) as db:
            first = Material(**base)
            second = Material(**base)
            db.add_all([first, second])
            db.commit()
            self.assertNotEqual(first.material_id, second.material_id)
            first_id = first.material_id
        with Session(self.engine) as db, self.assertRaises(IntegrityError):
            db.add(Material(material_id=first_id, **base))
            db.commit()
        for changes in ({'role': 'guest'}, {'user_id': 1}):
            with Session(self.engine) as db, self.assertRaises(IntegrityError):
                db.add(User(**({'full_name': 'Test', 'email': 'test@example.com', 'password_hash': self.password_hash, 'role': 'student'} | changes)))
                db.commit()

    def test_cors_contract_and_taxonomy(self):
        preflight = self.client.options('/api/auth/register', headers={'Origin': 'http://127.0.0.1:5173',
                      'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type'})
        self.assertEqual(preflight.status_code, 200)
        self.assertNotIn('access-control-allow-credentials', preflight.headers)
        self.assertEqual(self.client.get('/api/categories').json()['items'][0]['category_id'], 1)
        self.assertEqual(self.client.get('/api/courses').json()['items'][0]['course_id'], 1)
        self.assertEqual(self.client.get('/api/materials?limit=101').status_code, 422)
        paths = self.client.get('/openapi.json').json()['paths']
        self.assertIn('post', paths['/api/auth/register'])
        self.assertIn('get', paths['/api/admin/overview'])
