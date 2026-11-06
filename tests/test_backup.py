"""Backup, restore and reconciliation against real PostgreSQL and real files."""
from pathlib import Path
import json
import os
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from backend.app.core.config import settings
from backend.app.services import backup, reconcile
from sqlalchemy.orm import Session
from pg_base import PostgresCase, pdf_bytes

class BackupCase(PostgresCase):
    def setUp(self):
        super().setUp()
        self.backups = tempfile.TemporaryDirectory()
        self.addCleanup(self.backups.cleanup)
        self.destination = Path(self.backups.name)
        self.restore_url = make_url(self.url).set(database=make_url(self.url).database + '_restore').render_as_string(hide_password=False)

    def create(self, **options):
        return backup.create_backup(self.url, settings.uploads_dir, self.destination, **options)

class CreateAndVerify(BackupCase):
    def test_backup_contains_database_files_and_manifest(self):
        self.upload()
        path = self.create()
        self.assertEqual(sorted(item.name for item in path.iterdir()), ['database.dump', 'manifest.json', 'uploads.tar.gz'])
        manifest = backup.verify_backup(path)
        self.assertEqual(manifest['tables']['materials'], 1)
        self.assertEqual(manifest['tables']['users'], 3)
        self.assertEqual(manifest['files'], 1)
        self.assertEqual(manifest['alembic_revision'], '0002_admin_reports')

    def test_manifest_contains_no_credentials(self):
        path = self.create()
        text_ = (path / 'manifest.json').read_text(encoding='utf-8')
        self.assertNotIn(make_url(self.url).password, text_)
        self.assertNotIn('postgresql', text_)

    def test_changed_backup_fails_verification(self):
        path = self.create()
        with (path / 'uploads.tar.gz').open('ab') as archive:
            archive.write(b'tampered')
        with self.assertRaises(backup.BackupError):
            backup.verify_backup(path)

    def test_only_the_newest_backups_are_kept(self):
        created = [self.create(keep=2) for _ in range(4)]
        self.assertEqual(sorted(item.name for item in self.destination.iterdir()), sorted(path.name for path in created[-2:]))

    def test_rotation_leaves_unrelated_folders_alone(self):
        (self.destination / 'my-notes').mkdir()
        self.create(keep=1)
        self.create(keep=1)
        self.assertTrue((self.destination / 'my-notes').is_dir())

    def test_failed_backup_leaves_nothing_behind(self):
        unreachable = make_url(self.url).set(port=1).render_as_string(hide_password=False)
        with self.assertRaises(backup.BackupError) as caught:
            backup.create_backup(unreachable, settings.uploads_dir, self.destination)
        self.assertNotIn(make_url(self.url).password, str(caught.exception))
        self.assertEqual(list(self.destination.iterdir()), [])

class Restore(BackupCase):
    def test_restore_rebuilds_rows_and_files_in_a_separate_database(self):
        self.upload(title='Keep me')
        original = next(settings.uploads_dir.iterdir()).read_bytes()
        path = self.create()
        with tempfile.TemporaryDirectory() as restored_files:
            backup.prepare_restore_database(self.restore_url)
            self.addCleanup(backup.drop_restore_database, self.restore_url)
            report = backup.restore_backup(path, self.restore_url, Path(restored_files))
            self.assertEqual(report['tables']['materials'], 1)
            self.assertEqual(next(Path(restored_files).iterdir()).read_bytes(), original)
        engine = create_engine(self.restore_url)
        self.addCleanup(engine.dispose)
        with engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT title FROM materials')), 'Keep me')

    def test_recovery_after_total_loss_works_through_the_api(self):
        body = pdf_bytes()
        created = self.upload(title='Lost and found', body=body).json()
        path = self.create()
        with self.engine.begin() as connection:
            connection.execute(text('TRUNCATE materials CASCADE'))
        for item in settings.uploads_dir.iterdir():
            item.unlink()
        self.assertEqual(self.client.get('/api/materials').json()['total'], 0)
        self.engine.dispose()
        backup.restore_backup(path, self.url, settings.uploads_dir, allow_live=True)
        self.assertEqual(self.client.get('/api/materials').json()['items'][0]['title'], 'Lost and found')
        response = self.client.get(f"/api/materials/{created['material_id']}/download", headers=self.one)
        self.assertEqual(response.content, body)

    def test_restore_refuses_a_live_database_without_permission(self):
        path = self.create()
        with self.assertRaises(backup.BackupError):
            backup.restore_backup(path, self.url, settings.uploads_dir)

    def test_restore_refuses_a_changed_backup(self):
        path = self.create()
        (path / 'database.dump').write_bytes(b'broken')
        with self.assertRaises(backup.BackupError):
            backup.restore_backup(path, self.restore_url, settings.uploads_dir)

    def test_drill_proves_a_backup_restores_and_cleans_up(self):
        self.upload()
        self.upload(title='Second')
        report = backup.run_drill(self.url, settings.uploads_dir, self.destination)
        self.assertTrue(report['passed'])
        self.assertEqual(report['tables']['materials'], 2)
        self.assertEqual(report['files_checked'], 2)
        with self.engine.connect() as connection:
            exists = connection.scalar(text('SELECT count(*) FROM pg_database WHERE datname = :name'),
                                       {'name': make_url(self.restore_url).database})
        self.assertEqual(exists, 0)

class Reconciliation(PostgresCase):
    def test_finds_orphans_partials_and_missing_files(self):
        self.upload()
        kept = self.stored_files()[0]
        (settings.uploads_dir / 'orphan.pdf').write_bytes(b'x')
        (settings.uploads_dir / 'broken.pdf.part').write_bytes(b'x')
        gone = self.upload(title='Gone').json()
        with Session(self.engine) as db:
            found = reconcile.scan(db)
        self.assertEqual(found['orphan_files'], ['orphan.pdf'])
        self.assertEqual(found['partial_files'], ['broken.pdf.part'])
        self.assertEqual(found['missing_files'], [])
        (settings.uploads_dir / kept).unlink()
        with Session(self.engine) as db:
            self.assertEqual(reconcile.scan(db)['missing_files'], [kept])
        self.assertTrue(gone['material_id'])

    def test_admin_sees_counts_without_file_names(self):
        (settings.uploads_dir / 'orphan.pdf').write_bytes(b'x')
        response = self.client.get('/api/admin/storage-check', headers=self.admin)
        self.assertEqual(response.json(), {'orphan_files': 1, 'partial_files': 0, 'missing_files': 0})

    def test_cleanup_skips_recent_files_and_never_touches_referenced_ones(self):
        self.upload()
        referenced = self.stored_files()[0]
        old = settings.uploads_dir / 'old.pdf'
        fresh = settings.uploads_dir / 'fresh.pdf.part'
        old.write_bytes(b'x'); fresh.write_bytes(b'x')
        os.utime(old, (1, 1))
        os.utime(settings.uploads_dir / referenced, (1, 1))
        with Session(self.engine) as db:
            self.assertEqual(reconcile.remove_leftovers(db, min_age_seconds=3600), ['old.pdf'])
        self.assertEqual(sorted(self.stored_files()), sorted([referenced, 'fresh.pdf.part']))
