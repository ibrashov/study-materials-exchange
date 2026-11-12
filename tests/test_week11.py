"""Week 11: request limits, two-factor authentication, search indexes. Real PostgreSQL."""
import unittest
import pyotp
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.models.entities import Material, User
from backend.app.services import twofactor
from backend.app.services.ratelimit import RateLimiter, match_rule
from pg_base import PASSWORD, PostgresCase

class RateLimitUnit(unittest.TestCase):
    def test_sliding_window_and_retry_after(self):
        now = [0.0]
        limiter = RateLimiter(clock=lambda: now[0])
        rule = match_rule('POST', '/api/auth/login')
        self.assertTrue(all(limiter.check('1.1.1.1', rule)[0] for _ in range(rule.limit)))
        allowed, retry = limiter.check('1.1.1.1', rule)
        self.assertFalse(allowed)
        self.assertEqual(retry, rule.window)
        self.assertTrue(limiter.check('2.2.2.2', rule)[0])
        now[0] = rule.window + 0.1
        self.assertTrue(limiter.check('1.1.1.1', rule)[0])

    def test_rule_matching(self):
        self.assertEqual(match_rule('POST', '/api/auth/login').name, 'login')
        self.assertEqual(match_rule('POST', '/api/auth/register').name, 'register')
        self.assertEqual(match_rule('POST', '/api/materials').name, 'upload')
        self.assertEqual(match_rule('GET', '/api/materials/5/download').name, 'download')
        self.assertEqual(match_rule('GET', '/api/materials').name, 'default')

class RequestLimits(PostgresCase):
    def test_login_limited_with_retry_after(self):
        for _ in range(10):
            self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': 'wrong-password-1'})
        response = self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': PASSWORD})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()['error']['code'], 'http_429')
        self.assertGreaterEqual(int(response.headers['Retry-After']), 1)

    def test_register_limited_on_sixth_attempt(self):
        codes = [self.client.post('/api/auth/register', json={'full_name': 'N', 'email': f'n{i}@example.com', 'password': PASSWORD}).status_code
                 for i in range(6)]
        self.assertEqual(codes, [201] * 5 + [429])

    def test_limit_can_be_disabled_and_health_is_independent(self):
        settings.rate_limit_enabled = False
        try:
            codes = {self.client.post('/api/auth/login', json={'email': 'x@example.com', 'password': 'wrong-password-1'}).status_code for _ in range(12)}
        finally:
            settings.rate_limit_enabled = True
        self.assertEqual(codes, {401})
        for _ in range(11):
            self.client.post('/api/auth/login', json={'email': 'x@example.com', 'password': 'wrong-password-1'})
        self.assertEqual(self.client.get('/api/health').status_code, 200)

class TwoFactor(PostgresCase):
    def enable(self):
        data = self.client.post('/api/auth/2fa/setup', headers=self.one).json()
        code = pyotp.TOTP(data['secret']).now()
        self.assertEqual(self.client.post('/api/auth/2fa/enable', headers=self.one, json={'code': code}).status_code, 200)
        return data['secret']

    def test_secret_is_encrypted_and_enable_needs_valid_code(self):
        data = self.client.post('/api/auth/2fa/setup', headers=self.one).json()
        self.assertTrue(data['otpauth_uri'].startswith('otpauth://totp/'))
        self.assertEqual(self.client.post('/api/auth/2fa/enable', headers=self.one, json={'code': '000000'}).status_code, 401)
        with Session(self.engine) as db:
            user = db.scalar(select(User).where(User.email == 'one@example.com'))
            self.assertFalse(user.totp_enabled)
            self.assertNotEqual(user.totp_secret, data['secret'])
            self.assertEqual(twofactor.decrypt(user.totp_secret), data['secret'])

    def test_login_needs_otp_once_enabled(self):
        secret = self.enable()
        creds = {'email': 'one@example.com', 'password': PASSWORD}
        missing = self.client.post('/api/auth/login', json=creds)
        self.assertEqual((missing.status_code, missing.json()['error']['message']), (401, 'otp_required'))
        wrong = '000000' if pyotp.TOTP(secret).now() != '000000' else '111111'
        bad = self.client.post('/api/auth/login', json={**creds, 'otp': wrong})
        self.assertEqual((bad.status_code, bad.json()['error']['message']), (401, 'otp_invalid'))
        ok = self.client.post('/api/auth/login', json={**creds, 'otp': pyotp.TOTP(secret).now()})
        self.assertEqual(ok.status_code, 200)

    def test_disable_needs_password_and_code(self):
        secret = self.enable()
        code = pyotp.TOTP(secret).now()
        self.assertEqual(self.client.post('/api/auth/2fa/disable', headers=self.one, json={'code': code, 'password': 'wrong-password-1'}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/2fa/disable', headers=self.one, json={'code': code, 'password': PASSWORD}).status_code, 200)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': PASSWORD}).status_code, 200)

    def test_requires_authentication_and_admin_policy(self):
        self.assertEqual(self.client.post('/api/auth/2fa/setup').status_code, 401)
        settings.require_admin_2fa = True
        try:
            response = self.client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': PASSWORD})
        finally:
            settings.require_admin_2fa = False
        self.assertEqual(response.status_code, 403)

class SearchAndIndexes(PostgresCase):
    def test_search_matches_title_course_category_and_escapes_wildcards(self):
        with Session(self.engine) as db:
            db.add_all([Material(uploader_id=2, category_id=1, course_id=1, title='Linked lists 100%', file_path='a.pdf', file_size_bytes=10),
                        Material(uploader_id=2, category_id=1, course_id=1, title='Trees', file_path='b.pdf', file_size_bytes=10)])
            db.commit()
        total = lambda q: self.client.get('/api/materials', params={'q': q}).json()['total']
        self.assertEqual(total('linked'), 1)
        self.assertEqual(total('programming'), 2)
        self.assertEqual(total('lecture'), 2)
        self.assertEqual(total('%'), 1)
        self.assertEqual(total('nothing-like-this'), 0)

    def test_expected_indexes_exist(self):
        with self.engine.connect() as c:
            names = {r[0] for r in c.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public'"))}
        for name in ('ix_materials_title_trgm', 'ix_courses_name_trgm', 'ix_categories_name_trgm',
                     'ix_materials_course_newest', 'ix_materials_category_newest'):
            self.assertIn(name, names)

if __name__ == '__main__':
    unittest.main()
