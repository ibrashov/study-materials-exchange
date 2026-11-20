"""Study assistant endpoint. No database and no network: the Gemini call is mocked."""
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from backend.app.api.dependencies import current_user
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.main import app

FAKE_KEY = 'AQ.test-gemini-key-0000000000'


class FakeUser:
    role = 'student'
    is_active = True


def fake_response(status=200, text='Hello from the assistant'):
    response = mock.Mock(status_code=status)
    response.json.return_value = {'candidates': [{'content': {'parts': [{'text': text}]}}]}
    return response


class ChatEndpoint(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[current_user] = lambda: FakeUser()
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        for name, value in (('rate_limit_enabled', False), ('gemini_api_key', '')):
            patcher = mock.patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_disabled_without_key(self):
        self.assertEqual(self.client.get('/api/chat/status').json(), {'enabled': False})
        r = self.client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})
        self.assertEqual(r.status_code, 503)
        self.assertIn('GEMINI_API_KEY', r.json()['error']['message'])

    def test_requires_login(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: None  # no database needed to check the token
        r = self.client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})
        self.assertEqual(r.status_code, 401)

    def test_forwards_conversation_with_key(self):
        patcher = mock.patch.object(settings, 'gemini_api_key', FAKE_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        with mock.patch('backend.app.services.chatbot.httpx.post', return_value=fake_response()) as post:
            self.assertEqual(self.client.get('/api/chat/status').json(), {'enabled': True})
            r = self.client.post('/api/chat', json={'messages': [
                {'role': 'assistant', 'content': 'Welcome!'},   # leading assistant turn must be dropped
                {'role': 'user', 'content': 'How do I revise?'},
            ]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'reply': 'Hello from the assistant'})
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs['headers']['x-goog-api-key'], FAKE_KEY)
        self.assertEqual(kwargs['json']['contents'], [{'role': 'user', 'parts': [{'text': 'How do I revise?'}]}])
        self.assertIn(settings.gemini_model, post.call_args.args[0])

    def test_last_message_must_be_user(self):
        patcher = mock.patch.object(settings, 'gemini_api_key', FAKE_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        r = self.client.post('/api/chat', json={'messages': [{'role': 'assistant', 'content': 'hi'}]})
        self.assertEqual(r.status_code, 400)

    def test_upstream_error_does_not_leak_key_or_body(self):
        patcher = mock.patch.object(settings, 'gemini_api_key', FAKE_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        bad = mock.Mock(status_code=401, text=f'invalid key {FAKE_KEY}')
        with mock.patch('backend.app.services.chatbot.httpx.post', return_value=bad):
            r = self.client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})
        self.assertEqual(r.status_code, 503)
        self.assertNotIn(FAKE_KEY, r.text)

    def test_input_limits(self):
        patcher = mock.patch.object(settings, 'gemini_api_key', FAKE_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        too_long = {'messages': [{'role': 'user', 'content': 'x' * 2001}]}
        too_many = {'messages': [{'role': 'user', 'content': 'x'}] * 21}
        self.assertEqual(self.client.post('/api/chat', json=too_long).status_code, 422)
        self.assertEqual(self.client.post('/api/chat', json=too_many).status_code, 422)


if __name__ == '__main__':
    unittest.main()
