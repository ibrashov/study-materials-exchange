import unittest
from fastapi.testclient import TestClient
from backend.app.main import app


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'service': 'study-materials-backend'})

    def test_errors_and_docs(self):
        self.assertEqual(self.client.get('/api/missing').json(),
                         {'error': {'code': 'http_404', 'message': 'Not Found'}})
        self.assertEqual(self.client.post('/api/health').status_code, 405)
        self.assertEqual(self.client.get('/docs').status_code, 200)
        self.assertIn('/api/health', self.client.get('/openapi.json').json()['paths'])

    def test_cors(self):
        allowed = self.client.get('/api/health', headers={'Origin': 'http://127.0.0.1:5173'})
        self.assertEqual(allowed.headers['access-control-allow-origin'], 'http://127.0.0.1:5173')
        denied = self.client.get('/api/health', headers={'Origin': 'https://untrusted.example'})
        self.assertNotIn('access-control-allow-origin', denied.headers)
