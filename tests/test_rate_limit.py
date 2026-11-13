"""Request limiter on registration and login (real PostgreSQL test database)."""
from backend.app.core.config import settings
from pg_base import PASSWORD, PostgresCase

class RateLimit(PostgresCase):
    def setUp(self):
        super().setUp()
        self.saved = settings.login_limit, settings.register_limit, settings.rate_limit_enabled
        settings.login_limit, settings.register_limit, settings.rate_limit_enabled = 3, 2, True
        self.addCleanup(self.restore)

    def restore(self):
        settings.login_limit, settings.register_limit, settings.rate_limit_enabled = self.saved

    def login(self, password=PASSWORD):
        return self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': password})

    def register(self, n):
        return self.client.post('/api/auth/register', json={'full_name': 'New Person', 'email': f'new{n}@example.com', 'password': PASSWORD})

    def test_login_blocked_after_limit_with_retry_after(self):
        for _ in range(3):
            self.assertEqual(self.login('wrong-password-1').status_code, 401)
        blocked = self.login()
        self.assertEqual(blocked.status_code, 429)
        self.assertGreaterEqual(int(blocked.headers['Retry-After']), 1)

    def test_register_blocked_after_limit_and_no_row_created(self):
        self.assertEqual(self.register(1).status_code, 201)
        self.assertEqual(self.register(2).status_code, 201)
        self.assertEqual(self.register(3).status_code, 429)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'new3@example.com', 'password': PASSWORD}).status_code, 401)

    def test_window_expiry_allows_requests_again(self):
        from backend.app.services import rate_limit
        settings.rate_limit_window = 1
        self.addCleanup(setattr, settings, 'rate_limit_window', 60)
        for _ in range(3):
            self.login()
        self.assertEqual(self.login().status_code, 429)
        import time; time.sleep(1.1)
        self.assertEqual(self.login().status_code, 200)

    def test_disabled_limiter_never_blocks(self):
        settings.rate_limit_enabled = False
        for _ in range(6):
            self.assertEqual(self.login().status_code, 200)

    def test_limits_do_not_cross_endpoints(self):
        self.assertEqual(self.register(1).status_code, 201)
        self.assertEqual(self.register(2).status_code, 201)
        self.assertEqual(self.register(3).status_code, 429)
        self.assertEqual(self.login().status_code, 200)
