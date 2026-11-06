"""Admin panel, reports, moderation and negative cases against real PostgreSQL."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.models.entities import Material, User
from pg_base import PASSWORD, PostgresCase, pdf_bytes

class MaterialDeletion(PostgresCase):
    def test_owner_deletes_row_and_file(self):
        created = self.upload().json()
        self.assertEqual(len(self.stored_files()), 1)
        response = self.client.delete(f"/api/materials/{created['material_id']}", headers=self.one)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get('/api/materials').json()['total'], 0)
        self.assertEqual(self.stored_files(), [])

    def test_other_student_cannot_delete(self):
        created = self.upload().json()
        response = self.client.delete(f"/api/materials/{created['material_id']}", headers=self.two)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get('/api/materials').json()['total'], 1)
        self.assertEqual(len(self.stored_files()), 1)

    def test_admin_can_delete_any_material(self):
        created = self.upload().json()
        self.assertEqual(self.client.delete(f"/api/materials/{created['material_id']}", headers=self.admin).status_code, 204)

    def test_guest_cannot_delete(self):
        created = self.upload().json()
        self.assertEqual(self.client.delete(f"/api/materials/{created['material_id']}").status_code, 401)

    def test_deleting_unknown_material_is_404(self):
        self.assertEqual(self.client.delete('/api/materials/999', headers=self.admin).status_code, 404)

class Reports(PostgresCase):
    def test_course_report_counts_and_keeps_empty_courses_first(self):
        self.upload()
        report = self.client.get('/api/admin/reports/courses', headers=self.admin)
        self.assertEqual(report.status_code, 200)
        self.assertEqual([(row['course_code'], row['material_count']) for row in report.json()['items']],
                         [('DB101', 0), ('PROG101', 1)])

    def test_download_report_counts_real_downloads_only(self):
        first = self.upload(title='Popular').json()
        self.upload(title='Unread')
        for _ in range(3):
            self.assertEqual(self.client.get(f"/api/materials/{first['material_id']}/download", headers=self.two).status_code, 200)
        self.assertEqual(self.client.get(f"/api/materials/{first['material_id']}/download").status_code, 401)
        data = self.client.get('/api/admin/reports/downloads', headers=self.admin).json()
        self.assertEqual(data['total_downloads'], 3)
        self.assertEqual([(row['title'], row['download_count']) for row in data['items']], [('Popular', 3), ('Unread', 0)])
        self.assertEqual(data['items'][0]['course_name'], 'Programming')

    def test_reports_are_admin_only(self):
        for path in ('/api/admin/reports/courses', '/api/admin/reports/downloads', '/api/admin/users', '/api/admin/storage-check'):
            self.assertEqual(self.client.get(path).status_code, 401, path)
            self.assertEqual(self.client.get(path, headers=self.one).status_code, 403, path)

class UserManagement(PostgresCase):
    def test_list_users_hides_private_fields(self):
        data = self.client.get('/api/admin/users', headers=self.admin).json()
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['items'][1]['email'], 'one@example.com')
        self.assertEqual(data['items'][1]['is_active'], True)
        self.assertNotIn('password_hash', data['items'][1])

    def test_user_search_filters_by_name_or_email(self):
        data = self.client.get('/api/admin/users?q=TWO', headers=self.admin).json()
        self.assertEqual([row['email'] for row in data['items']], ['two@example.com'])

    def test_promote_student_to_admin_takes_effect_immediately(self):
        response = self.client.patch('/api/admin/users/2', headers=self.admin, json={'role': 'admin'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['role'], 'admin')
        self.assertEqual(self.client.get('/api/admin/overview', headers=self.one).status_code, 200)

    def test_blocked_user_loses_access_and_cannot_log_in(self):
        token = self.one
        self.assertEqual(self.client.patch('/api/admin/users/2', headers=self.admin, json={'is_active': False}).status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me', headers=token).status_code, 403)
        self.assertEqual(self.upload(headers=token).status_code, 403)
        login = self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': PASSWORD})
        self.assertEqual(login.status_code, 403)

    def test_unblocked_user_can_log_in_again(self):
        self.client.patch('/api/admin/users/2', headers=self.admin, json={'is_active': False})
        self.client.patch('/api/admin/users/2', headers=self.admin, json={'is_active': True})
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': PASSWORD}).status_code, 200)

    def test_wrong_password_for_blocked_user_stays_generic(self):
        self.client.patch('/api/admin/users/2', headers=self.admin, json={'is_active': False})
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'one@example.com', 'password': 'wrong-password-1'}).status_code, 401)

    def test_admin_cannot_lock_themselves_out(self):
        self.assertEqual(self.client.patch('/api/admin/users/1', headers=self.admin, json={'role': 'student'}).status_code, 409)
        self.assertEqual(self.client.patch('/api/admin/users/1', headers=self.admin, json={'is_active': False}).status_code, 409)

    def test_invalid_changes_are_rejected(self):
        self.assertEqual(self.client.patch('/api/admin/users/2', headers=self.admin, json={'role': 'owner'}).status_code, 422)
        self.assertEqual(self.client.patch('/api/admin/users/2', headers=self.admin, json={'password_hash': 'x'}).status_code, 422)
        self.assertEqual(self.client.patch('/api/admin/users/2', headers=self.admin, json={}).status_code, 422)
        self.assertEqual(self.client.patch('/api/admin/users/999', headers=self.admin, json={'role': 'admin'}).status_code, 404)

    def test_student_cannot_change_users(self):
        self.assertEqual(self.client.patch('/api/admin/users/2', headers=self.one, json={'role': 'admin'}).status_code, 403)

class Taxonomy(PostgresCase):
    def test_admin_adds_category_and_course(self):
        category = self.client.post('/api/admin/categories', headers=self.admin, json={'category_name': '  Exam Prep '})
        self.assertEqual(category.status_code, 201)
        self.assertEqual(category.json()['category_name'], 'Exam Prep')
        course = self.client.post('/api/admin/courses', headers=self.admin, json={'course_name': 'Networks', 'course_code': 'net201'})
        self.assertEqual(course.status_code, 201)
        self.assertEqual(course.json()['course_code'], 'NET201')
        self.assertEqual(len(self.client.get('/api/categories').json()['items']), 2)

    def test_duplicates_are_rejected(self):
        self.assertEqual(self.client.post('/api/admin/categories', headers=self.admin, json={'category_name': 'Lecture Notes'}).status_code, 409)
        self.assertEqual(self.client.post('/api/admin/courses', headers=self.admin, json={'course_name': 'Again', 'course_code': 'prog101'}).status_code, 409)

    def test_blank_values_and_students_are_rejected(self):
        self.assertEqual(self.client.post('/api/admin/categories', headers=self.admin, json={'category_name': '   '}).status_code, 422)
        self.assertEqual(self.client.post('/api/admin/categories', headers=self.one, json={'category_name': 'X'}).status_code, 403)
        self.assertEqual(self.client.post('/api/admin/courses', json={'course_name': 'X', 'course_code': 'Y'}).status_code, 401)

class NegativeCases(PostgresCase):
    def test_encrypted_pdf_is_rejected_without_leftovers(self):
        self.assertEqual(self.upload(body=pdf_bytes(password='secret')).status_code, 415)
        self.assertEqual(self.stored_files(), [])
        self.assertEqual(self.client.get('/api/materials').json()['total'], 0)

    def test_renamed_text_file_is_rejected(self):
        self.assertEqual(self.upload(body=b'not really a pdf').status_code, 415)
        self.assertEqual(self.stored_files(), [])

    def test_missing_stored_file_gives_404_and_is_not_counted(self):
        created = self.upload().json()
        (settings.uploads_dir / self.stored_files()[0]).unlink()
        response = self.client.get(f"/api/materials/{created['material_id']}/download", headers=self.one)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get('/api/admin/reports/downloads', headers=self.admin).json()['total_downloads'], 0)

    def test_stored_path_outside_uploads_is_refused(self):
        created = self.upload().json()
        with Session(self.engine) as db:
            db.get(Material, created['material_id']).file_path = '../outside.pdf'
            db.commit()
        self.assertEqual(self.client.get(f"/api/materials/{created['material_id']}/download", headers=self.one).status_code, 404)

    def test_client_cannot_choose_uploader(self):
        response = self.client.post('/api/materials', headers=self.one, data={'title': 'Mine', 'category_id': 1, 'course_id': 1, 'uploader_id': 3},
                                    files={'file': ('n.pdf', pdf_bytes(), 'application/pdf')})
        self.assertEqual(response.json()['uploader_id'], 2)

    def test_search_treats_wildcards_literally(self):
        self.upload(title='Plain notes')
        self.assertEqual(self.client.get('/api/materials', params={'q': '%'}).json()['total'], 0)

    def test_public_responses_never_expose_file_path(self):
        self.upload()
        self.assertNotIn('file_path', self.client.get('/api/materials').json()['items'][0])
