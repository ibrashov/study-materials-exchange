"""Integration tests for Trash, Gamification, and Scheduled Backups (real PostgreSQL)."""
import json
from pathlib import Path
import tempfile
from unittest import mock

import pyotp
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.services import backup_scheduler
from pg_base import PostgresCase

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

        # Student Two downloads the same material 3 times -> XP only once: +5 to Two, +10 to One (no farming)
        for _ in range(3):
            self.assertEqual(self.client.get(f'/api/materials/{mid}/download', headers=self.two).status_code, 200)
        # Downloading your own material earns nothing
        self.assertEqual(self.client.get(f'/api/materials/{mid}/download', headers=self.one).status_code, 200)

        p2 = self.client.get('/api/gamification/me', headers=self.two).json()
        self.assertEqual(p2['xp_points'], 5)
        self.assertNotIn('curious_learner', {b['code'] for b in p2['badges'] if b['earned']})
        p1 = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p1['xp_points'], 60)
        self.assertEqual(p1['total_downloads_received'], 4)

        # Student One enables 2FA -> +25 XP + security_champion badge (60 + 25 = 85 XP)
        setup = self.client.post('/api/auth/2fa/setup', headers=self.one).json()
        code = pyotp.TOTP(setup['secret']).now()
        self.assertEqual(self.client.post('/api/auth/2fa/enable', headers=self.one, json={'code': code}).status_code, 200)

        p1_after = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p1_after['xp_points'], 85)
        self.assertIn('security_champion', {b['code'] for b in p1_after['badges'] if b['earned']})

        # Upload 2 more materials -> +100 XP => 185 XP (level 3 scholar + rising_star badge!)
        lab = self.upload(headers=self.one, title='Algorithms Lab').json()['material_id']
        exam = self.upload(headers=self.one, title='Algorithms Exam').json()['material_id']
        p1_scholar = self.client.get('/api/gamification/me', headers=self.one).json()
        self.assertEqual(p1_scholar['xp_points'], 185)
        self.assertEqual(p1_scholar['level'], 3)
        self.assertEqual(p1_scholar['level_code'], 'scholar')
        self.assertIn('rising_star', {b['code'] for b in p1_scholar['badges'] if b['earned']})

        # Student Two downloads 2 new materials -> 3 distinct downloads: 15 XP and curious_learner; One +20
        for other in (lab, exam):
            self.assertEqual(self.client.get(f'/api/materials/{other}/download', headers=self.two).status_code, 200)
        p2 = self.client.get('/api/gamification/me', headers=self.two).json()
        self.assertEqual(p2['xp_points'], 15)
        self.assertIn('curious_learner', {b['code'] for b in p2['badges'] if b['earned']})

        # Public leaderboard ranks Student One first and exposes no private fields
        board = self.client.get('/api/gamification/leaderboard').json()['items']
        self.assertEqual(board[0]['full_name'], 'Student One')
        self.assertEqual(board[0]['xp_points'], 205)
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
