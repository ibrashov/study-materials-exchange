"""Integration tests for Trash, Gamification, Scheduled Backups, and AI Agent (real PostgreSQL)."""
import json
from pathlib import Path
import tempfile
from unittest import mock

import pyotp
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.services import backup_scheduler, chatbot
from pg_base import PostgresCase

FAKE_KEY = 'sk-ant-test-agent-000000000000'


def mock_anthropic_response(content, status=200):
    resp = mock.Mock(status_code=status)
    resp.json.return_value = {'content': content}
    return resp


class TrashTests(PostgresCase):
    def test_trash_restore_and_visibility(self):
        created = self.upload(title='Calculus Summary').json()
        mid = created['material_id']

        # Move to trash
        trashed = self.client.post(f'/api/materials/{mid}/trash', headers=self.one)
        self.assertEqual(trashed.status_code, 200, trashed.text)
        self.assertIsNotNone(trashed.json()['deleted_at'])

        # Hidden from public catalog, downloads, and admin active counts
        self.assertEqual(self.client.get('/api/materials').json()['total'], 0)
        self.assertEqual(self.client.get(f'/api/materials/{mid}/download', headers=self.one).status_code, 404)
        self.assertEqual(self.client.get('/api/admin/overview', headers=self.admin).json()['total_materials'], 0)
        # File remains safely stored and not reported as orphan
        self.assertEqual(len(self.stored_files()), 1)
        self.assertEqual(self.client.get('/api/admin/storage-check', headers=self.admin).json()['orphan_files'], 0)

        # Visible to owner and admin, hidden from another student
        self.assertEqual(self.client.get('/api/materials/trash', headers=self.one).json()['total'], 1)
        self.assertEqual(self.client.get('/api/materials/trash', headers=self.two).json()['total'], 0)
        self.assertEqual(self.client.get('/api/materials/trash', headers=self.admin).json()['total'], 1)

        # Other student cannot restore
        self.assertEqual(self.client.post(f'/api/materials/{mid}/restore', headers=self.two).status_code, 403)

        # Owner restores from trash
        restored = self.client.post(f'/api/materials/{mid}/restore', headers=self.one)
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(self.client.get('/api/materials').json()['total'], 1)
        self.assertEqual(self.client.get('/api/materials/trash', headers=self.one).json()['total'], 0)
        self.assertEqual(self.client.get(f'/api/materials/{mid}/download', headers=self.one).status_code, 200)

    def test_empty_trash_permanently_deletes_trashed_only(self):
        keep = self.upload(title='Keep Active').json()
        drop = self.upload(title='Drop Me').json()
        self.assertEqual(self.client.delete(f"/api/materials/{drop['material_id']}?trash=true", headers=self.one).status_code, 204)
        self.assertEqual(len(self.stored_files()), 2)

        emptied = self.client.delete('/api/materials/trash', headers=self.one)
        self.assertEqual(emptied.status_code, 200)
        self.assertEqual(emptied.json(), {'deleted_count': 1})
        self.assertEqual(self.client.get('/api/materials/trash', headers=self.one).json()['total'], 0)
        self.assertEqual(self.client.get('/api/materials').json()['total'], 1)
        self.assertEqual(self.client.get('/api/materials').json()['items'][0]['material_id'], keep['material_id'])
        self.assertEqual(len(self.stored_files()), 1)

    def test_other_student_cannot_trash(self):
        created = self.upload(title='Private Owner').json()
        self.assertEqual(self.client.post(f"/api/materials/{created['material_id']}/trash", headers=self.two).status_code, 403)


class GamificationTests(PostgresCase):
    def test_upload_download_2fa_xp_badges_and_leaderboard(self):
        # Student One uploads a material -> +50 XP, level 2 (contributor), first_upload badge
        created = self.upload(headers=self.one, title='Algorithms Lecture').json()
        mid = created['material_id']

        p1 = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p1['xp_points'], 50)
        self.assertEqual(p1['level'], 2)
        self.assertEqual(p1['level_code'], 'contributor')
        self.assertEqual(p1['current_streak'], 1)
        earned_one = {b['code'] for b in p1['badges'] if b['earned']}
        self.assertIn('first_upload', earned_one)

        # Student Two downloads Student One's material 3 times -> +15 XP to Two (curious_learner), +30 XP to One
        for _ in range(3):
            self.assertEqual(self.client.get(f'/api/materials/{mid}/download', headers=self.two).status_code, 200)

        p2 = self.client.get('/api/gamification/me', headers=self.two).json()
        self.assertEqual(p2['xp_points'], 15)
        self.assertIn('curious_learner', {b['code'] for b in p2['badges'] if b['earned']})

        # Student One enables 2FA -> +25 XP + security_champion badge (total 50 + 30 + 25 = 105 XP)
        setup = self.client.post('/api/auth/2fa/setup', headers=self.one).json()
        code = pyotp.TOTP(setup['secret']).now()
        self.assertEqual(self.client.post('/api/auth/2fa/enable', headers=self.one, json={'code': code}).status_code, 200)

        p1_after = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p1_after['xp_points'], 105)
        self.assertIn('security_champion', {b['code'] for b in p1_after['badges'] if b['earned']})

        # Upload 1 more material -> +50 XP => 155 XP (level 3 scholar + rising_star badge!)
        self.upload(headers=self.one, title='Algorithms Lab')
        p1_scholar = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p1_scholar['xp_points'], 155)
        self.assertEqual(p1_scholar['level'], 3)
        self.assertEqual(p1_scholar['level_code'], 'scholar')
        self.assertIn('rising_star', {b['code'] for b in p1_scholar['badges'] if b['earned']})

        # Public leaderboard ranks Student One first and exposes no private fields
        board = self.client.get('/api/gamification/leaderboard').json()['items']
        self.assertEqual(board[0]['full_name'], 'Student One')
        self.assertEqual(board[0]['xp_points'], 155)
        self.assertEqual(board[1]['full_name'], 'Student Two')
        self.assertNotIn('email', board[0])

        # Badge catalog endpoint works publicly
        catalog = self.client.get('/api/gamification/badges').json()['items']
        self.assertGreaterEqual(len(catalog), 7)


class ScheduledBackupAdminTests(PostgresCase):
    def setUp(self):
        super().setUp()
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM app_settings WHERE key = 'backup_schedule'"))
        self.backups_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.backups_dir.cleanup)
        self.prev_backups = settings.backups_dir
        settings.backups_dir = Path(self.backups_dir.name)
        backup_scheduler.scheduler.reset_state()

    def tearDown(self):
        settings.backups_dir = self.prev_backups
        backup_scheduler.scheduler.reset_state()
        super().tearDown()

    def test_admin_schedule_persistence_and_manual_run(self):
        # Authorization enforced
        self.assertEqual(self.client.get('/api/admin/backups').status_code, 401)
        self.assertEqual(self.client.get('/api/admin/backups', headers=self.one).status_code, 403)

        # Update schedule and verify persistence
        updated = self.client.patch(
            '/api/admin/backups/schedule',
            headers=self.admin,
            json={'enabled': True, 'interval_hours': 12, 'hour_utc': 3, 'keep': 5},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        data = updated.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['interval_hours'], 12)
        self.assertEqual(data['keep'], 5)
        self.assertIsNotNone(data['next_run_at'])

        # Upload a file and trigger an immediate backup via admin API
        self.upload(title='Backed Up Note')
        run = self.client.post('/api/admin/backups/run', headers=self.admin)
        self.assertEqual(run.status_code, 201, run.text)
        created = run.json()
        self.assertTrue(created['verified'])
        self.assertEqual(created['tables']['materials'], 1)
        self.assertEqual(created['files'], 1)

        # Listing returns persisted schedule + verified backup entry
        listed = self.client.get('/api/admin/backups', headers=self.admin).json()
        self.assertTrue(listed['schedule']['enabled'])
        self.assertEqual(listed['schedule']['last_status'], 'ok')
        self.assertEqual(len(listed['items']), 1)
        self.assertEqual(listed['items'][0]['name'], created['name'])


class AiAgentTests(PostgresCase):
    def setUp(self):
        super().setUp()
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM app_settings WHERE key = 'agent_config'"))
        self.key_patch = mock.patch.object(settings, 'anthropic_api_key', FAKE_KEY)
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def test_admin_agent_config_and_validation(self):
        self.assertEqual(self.client.get('/api/admin/agent', headers=self.one).status_code, 403)

        cfg = self.client.get('/api/admin/agent', headers=self.admin)
        self.assertEqual(cfg.status_code, 200)
        self.assertTrue(cfg.json()['api_key_configured'])
        self.assertIn('search_materials', cfg.json()['available_tools'])

        # Reject unknown tools
        bad = self.client.patch('/api/admin/agent', headers=self.admin, json={'enabled_tools': ['nonexistent_tool']})
        self.assertEqual(bad.status_code, 422)

        # Persist valid customization
        saved = self.client.patch(
            '/api/admin/agent',
            headers=self.admin,
            json={
                'model': 'claude-sonnet-5-5',
                'max_tokens': 1024,
                'temperature': 0.2,
                'tools_enabled': True,
                'max_tool_steps': 3,
                'enabled_tools': ['search_materials', 'get_my_progress', 'get_my_trash'],
                'system_prompt': 'Custom university study agent prompt.',
            },
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()['max_tokens'], 1024)
        self.assertEqual(saved.json()['enabled_tools'], ['search_materials', 'get_my_progress', 'get_my_trash'])

        # Signed-in user sees updated agent capabilities
        info = self.client.get('/api/chat/agent', headers=self.one).json()
        self.assertTrue(info['enabled'])
        self.assertEqual(info['active_tools'], ['search_materials', 'get_my_progress', 'get_my_trash'])

    def test_agent_executes_live_platform_tools(self):
        # Seed active material and trashed material for Student One
        self.upload(headers=self.one, title='Linear Algebra Matrices')
        trashed = self.upload(headers=self.one, title='Old Draft Notes').json()
        self.client.post(f"/api/materials/{trashed['material_id']}/trash", headers=self.one)

        tool_turn = mock_anthropic_response([
            {'type': 'tool_use', 'id': 'tu_1', 'name': 'search_materials', 'input': {'query': 'Linear'}},
            {'type': 'tool_use', 'id': 'tu_2', 'name': 'get_my_progress', 'input': {}},
            {'type': 'tool_use', 'id': 'tu_3', 'name': 'get_my_trash', 'input': {}},
        ])
        final_turn = mock_anthropic_response([
            {'type': 'text', 'text': 'Found Linear Algebra Matrices! You have 100 XP and 1 item in Trash.'}
        ])

        with mock.patch('backend.app.services.chatbot.httpx.post', side_effect=[tool_turn, final_turn]) as post:
            resp = self.client.post(
                '/api/chat',
                headers=self.one,
                json={'messages': [{'role': 'user', 'content': 'Find Linear notes and check my progress'}], 'include_meta': True},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIn('Linear Algebra Matrices', body['reply'])
        self.assertEqual(body['tools_used'], ['search_materials', 'get_my_progress', 'get_my_trash'])
        self.assertEqual(post.call_count, 2)

        # Inspect actual tool_result payloads sent back to Anthropic on turn 2
        second_payload = post.call_args_list[1].kwargs['json']
        tool_results = second_payload['messages'][-1]['content']
        search_res = json.loads(tool_results[0]['content'])
        progress_res = json.loads(tool_results[1]['content'])
        trash_res = json.loads(tool_results[2]['content'])

        self.assertEqual(search_res['count'], 1)
        self.assertEqual(search_res['materials'][0]['title'], 'Linear Algebra Matrices')
        self.assertEqual(progress_res['xp_points'], 100)
        self.assertEqual(trash_res['count'], 1)
        self.assertEqual(trash_res['items'][0]['title'], 'Old Draft Notes')

        # Daily AI study session awards +5 XP once per day
        p_after = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p_after['xp_points'], 105)


class InceptionLabsAgentTests(PostgresCase):
    def setUp(self):
        super().setUp()
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM app_settings WHERE key = 'agent_config'"))
        self.patches = [
            mock.patch.object(settings, 'inception_api_key', 'sk_inception_test_secret_12345'),
            mock.patch.object(settings, 'anthropic_api_key', ''),
            mock.patch.object(settings, 'inception_model', 'mercury-2'),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_inception_agent_openai_tool_calling_and_error_redaction(self):
        self.upload(headers=self.one, title='Database Normalization Guide')

        # Status and agent info report Inception Labs provider & mercury-2
        self.assertEqual(self.client.get('/api/chat/status', headers=self.one).json(), {'enabled': True})
        info = self.client.get('/api/chat/agent', headers=self.one).json()
        self.assertEqual(info['provider'], 'inception')
        self.assertEqual(info['model'], 'mercury-2')

        # Turn 1: Mercury requests OpenAI-format tool_calls
        turn1 = mock.Mock(status_code=200)
        turn1.json.return_value = {
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': '',
                    'tool_calls': [{
                        'id': 'call_abc1',
                        'type': 'function',
                        'function': {
                            'name': 'search_materials',
                            'arguments': json.dumps({'query': 'Normalization'}),
                        },
                    }],
                },
            }],
        }
        # Turn 2: Mercury returns final answer
        turn2 = mock.Mock(status_code=200)
        turn2.json.return_value = {
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': 'I found Database Normalization Guide for you!',
                },
            }],
        }

        with mock.patch('backend.app.services.chatbot.httpx.post', side_effect=[turn1, turn2]) as post:
            resp = self.client.post(
                '/api/chat',
                headers=self.one,
                json={'messages': [{'role': 'user', 'content': 'Find normalization notes'}], 'include_meta': True},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body['provider'], 'inception')
        self.assertEqual(body['model'], 'mercury-2')
        self.assertEqual(body['tools_used'], ['search_materials'])
        self.assertIn('Database Normalization Guide', body['reply'])

        # Verify Inception Labs endpoint, Bearer auth, and OpenAI tool result message
        first_call = post.call_args_list[0]
        self.assertEqual(first_call.args[0], 'https://api.inceptionlabs.ai/v1/chat/completions')
        self.assertEqual(first_call.kwargs['headers']['Authorization'], 'Bearer sk_inception_test_secret_12345')
        self.assertEqual(first_call.kwargs['json']['model'], 'mercury-2')
        self.assertEqual(first_call.kwargs['json']['tools'][0]['type'], 'function')

        second_messages = post.call_args_list[1].kwargs['json']['messages']
        tool_msg = second_messages[-1]
        self.assertEqual(tool_msg['role'], 'tool')
        self.assertEqual(tool_msg['tool_call_id'], 'call_abc1')
        self.assertIn('Database Normalization Guide', tool_msg['content'])

        # Upstream error never leaks API key
        bad = mock.Mock(status_code=401, text='invalid key sk_inception_test_secret_12345')
        with mock.patch('backend.app.services.chatbot.httpx.post', return_value=bad):
            err_resp = self.client.post('/api/chat', headers=self.one, json={'messages': [{'role': 'user', 'content': 'hi'}]})
        self.assertEqual(err_resp.status_code, 503)
        self.assertNotIn('sk_inception_test_secret_12345', err_resp.text)
