"""Forward and backward migrations against the disposable test database."""
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from backend.app.core.config import settings
from pg_base import PostgresCase

class Migrations(PostgresCase):
    def migrate(self, action, target):
        original = settings.database_url
        try:
            settings.database_url = self.url
            action(Config('alembic.ini'), target)
        finally:
            settings.database_url = original
        self.engine.dispose()

    def tearDown(self):
        self.migrate(command.upgrade, 'head')
        super().tearDown()

    def columns(self, table):
        return {column['name'] for column in inspect(self.engine).get_columns(table)}

    def test_downgrade_removes_new_columns_and_keeps_rows(self):
        self.upload(title='Survivor')
        self.migrate(command.downgrade, '0001_week10')
        self.assertNotIn('download_count', self.columns('materials'))
        self.assertNotIn('is_active', self.columns('users'))
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT title FROM materials')), 'Survivor')

    def test_upgrade_gives_existing_rows_safe_defaults(self):
        self.upload()
        self.migrate(command.downgrade, '0001_week10')
        self.migrate(command.upgrade, 'head')
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT download_count FROM materials')), 0)
            self.assertEqual(connection.scalar(text('SELECT bool_and(is_active) FROM users')), True)

    def test_full_downgrade_and_rebuild(self):
        self.migrate(command.downgrade, 'base')
        self.assertNotIn('materials', inspect(self.engine).get_table_names())
        self.migrate(command.upgrade, 'head')
        self.assertIn('download_count', self.columns('materials'))
