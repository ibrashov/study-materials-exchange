"""Gamification rules that keep XP honest, and public student profiles (real PostgreSQL)."""
from datetime import date, datetime, timedelta, timezone

import pyotp
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.models.entities import User
from backend.app.services import gamification
from pg_base import PostgresCase


class GamificationRules(PostgresCase):
    def me(self, headers):
        return self.client.get('/api/gamification/me', headers=headers).json()

    def download(self, material_id, headers):
        response = self.client.get(f'/api/materials/{material_id}/download', headers=headers)
        self.assertEqual(response.status_code, 200, response.text)

    def test_repeat_own_and_admin_downloads_earn_nothing(self):
        mid = self.upload(headers=self.one, title='Graphs').json()['material_id']
        for _ in range(12):
            self.download(mid, self.one)            # own material: no XP, no popular_notes badge
        for _ in range(3):
            self.download(mid, self.admin)          # administrators review, they do not study
        for _ in range(5):
            self.download(mid, self.two)            # repeat downloads: paid once
        one, two = self.me(self.one), self.me(self.two)
        self.assertEqual(one['xp_points'], 60)
        self.assertNotIn('popular_notes', {b['code'] for b in one['badges'] if b['earned']})
        self.assertEqual(two['xp_points'], 5)
        self.assertEqual([e['action'] for e in two['recent_events']], ['download_material'])
        self.assertEqual(two['recent_events'][0]['material_title'], 'Graphs')

    def test_trash_takes_upload_xp_back_and_restore_returns_it(self):
        mid = self.upload(headers=self.one, title='Draft').json()['material_id']
        self.assertEqual(self.me(self.one)['xp_points'], 50)

        self.assertEqual(self.client.post(f'/api/materials/{mid}/trash', headers=self.one).status_code, 200)
        self.assertEqual(self.me(self.one)['xp_points'], 0)
        self.assertEqual(self.client.post(f'/api/materials/{mid}/restore', headers=self.one).status_code, 200)
        self.assertEqual(self.me(self.one)['xp_points'], 50)

        # An administrator moving it to Trash also takes the XP back, emptying Trash changes nothing.
        self.assertEqual(self.client.post(f'/api/materials/{mid}/trash', headers=self.admin).status_code, 200)
        self.assertEqual(self.client.delete('/api/materials/trash', headers=self.one).json()['deleted_count'], 1)
        profile = self.me(self.one)
        self.assertEqual(profile['xp_points'], 0)
        self.assertEqual(profile['recent_events'][0]['action'], 'upload_revoked')
        self.assertEqual(profile['recent_events'][0]['points'], -50)

    def test_upload_delete_reupload_cannot_farm(self):
        for _ in range(3):
            mid = self.upload(headers=self.one, title='Same notes').json()['material_id']
            self.assertEqual(self.client.delete(f'/api/materials/{mid}', headers=self.one).status_code, 204)
        self.assertEqual(self.me(self.one)['xp_points'], 0)
        self.upload(headers=self.one, title='Same notes')
        self.assertEqual(self.me(self.one)['xp_points'], 50)

    def test_leaderboard_ranks_only_students_with_xp(self):
        self.upload(headers=self.one, title='Notes')
        board = self.client.get('/api/gamification/leaderboard').json()['items']
        self.assertEqual([row['full_name'] for row in board], ['Student One'])
        # Admin XP (e.g. from 2FA) never puts an administrator on the student leaderboard.
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE users SET xp_points = 999 WHERE role = 'admin'"))
        board = self.client.get('/api/gamification/leaderboard').json()['items']
        self.assertEqual([row['full_name'] for row in board], ['Student One'])

    def test_badges_are_idempotent(self):
        self.upload(headers=self.one, title='Notes')
        with Session(self.engine) as db:
            user = db.get(User, 2)
            self.assertEqual(gamification.evaluate_badges(db, user), [])
            db.execute(text("DELETE FROM user_badges"))
            self.assertEqual(gamification.evaluate_badges(db, user), ['first_upload'])
            self.assertEqual(gamification.evaluate_badges(db, user), [])
            db.commit()

    def test_study_day_and_streak_follow_local_time(self):
        # 20:30 UTC on 20 Nov is already 01:30 on 21 Nov in Almaty (UTC+5).
        late = datetime(2026, 11, 20, 20, 30, tzinfo=timezone.utc)
        self.assertEqual(gamification.local_today(late), date(2026, 11, 21))
        today = gamification.local_today()
        self.assertEqual(gamification.effective_streak(4, today - timedelta(days=1), today), 4)
        self.assertEqual(gamification.effective_streak(4, today - timedelta(days=2), today), 0)

        with self.engine.begin() as connection:
            connection.execute(text("UPDATE users SET current_streak = 2, longest_streak = 2, last_activity_date = :d "
                                    "WHERE user_id = 2"), {'d': today - timedelta(days=1)})
        self.upload(headers=self.one, title='Day three')
        profile = self.me(self.one)
        self.assertEqual(profile['current_streak'], 3)
        self.assertIn('streak_starter', {b['code'] for b in profile['badges'] if b['earned']})

        # A streak that was not continued yesterday is shown as 0 on the leaderboard.
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE users SET last_activity_date = :d WHERE user_id = 2"),
                               {'d': today - timedelta(days=5)})
        self.assertEqual(self.client.get('/api/gamification/leaderboard').json()['items'][0]['current_streak'], 0)


class StudentProfiles(PostgresCase):
    def setUp(self):
        super().setUp()
        self.mid = self.upload(headers=self.one, title='Compilers').json()['material_id']
        self.other = self.upload(headers=self.two, title='Networks').json()['material_id']
        self.client.get(f'/api/materials/{self.other}/download', headers=self.one)
        self.client.get(f'/api/materials/{self.mid}/download', headers=self.two)
        setup = self.client.post('/api/auth/2fa/setup', headers=self.one).json()
        code = pyotp.TOTP(setup['secret']).now()
        self.assertEqual(self.client.post('/api/auth/2fa/enable', headers=self.one, json={'code': code}).status_code, 200)

    def test_anyone_can_open_a_student_profile(self):
        response = self.client.get('/api/gamification/users/2')
        self.assertEqual(response.status_code, 200, response.text)
        profile = response.json()
        self.assertEqual(profile['full_name'], 'Student One')
        self.assertFalse(profile['is_self'])
        self.assertEqual(profile['rank'], 1)
        self.assertEqual(profile['xp_points'], 50 + 5 + 10 + 25)
        self.assertEqual(profile['materials_count'], 1)
        self.assertEqual(profile['uploads'][0]['title'], 'Compilers')
        self.assertEqual(profile['uploads'][0]['course_code'], 'PROG101')
        self.assertEqual(profile['students_reached'], 1)
        self.assertEqual(profile['materials_studied'], 1)
        self.assertEqual(profile['activity_days'][-1]['date'], profile['today'])
        self.assertNotIn('email', profile)

    def test_others_do_not_see_private_details(self):
        public = self.client.get('/api/gamification/users/2', headers=self.two).json()
        self.assertNotIn('security_champion', {b['code'] for b in public['badges']})
        self.assertNotIn('enable_2fa', {e['action'] for e in public['recent_events']})
        self.assertNotIn('security', {s['source'] for s in public['xp_breakdown']})
        studied = [e for e in public['recent_events'] if e['action'] == 'download_material']
        self.assertEqual(studied[0]['material_title'], None)
        self.assertNotIn('Networks', studied[0]['description'])

        own = self.client.get('/api/gamification/users/2', headers=self.one).json()
        self.assertTrue(own['is_self'])
        self.assertIn('security_champion', {b['code'] for b in own['badges'] if b['earned']})
        self.assertIn('enable_2fa', {e['action'] for e in own['recent_events']})
        self.assertEqual(sum(s['xp'] for s in own['xp_breakdown']), own['xp_points'])

    def test_admins_blocked_and_missing_users_have_no_profile(self):
        self.assertEqual(self.client.get('/api/gamification/users/1').status_code, 404)
        self.assertEqual(self.client.get('/api/gamification/users/999').status_code, 404)
        self.assertEqual(self.client.get('/api/gamification/users/0').status_code, 422)
        with self.engine.begin() as connection:
            connection.execute(text('UPDATE users SET is_active = false WHERE user_id = 3'))
        self.assertEqual(self.client.get('/api/gamification/users/3').status_code, 404)

    def test_expired_token_still_sees_public_profile(self):
        response = self.client.get('/api/gamification/users/2', headers={'Authorization': 'Bearer not-a-token'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_self'])
