import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / 'database'


def sql(name):
    return (DATABASE / name).read_text(encoding='utf-8')


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys = ON')
        self.db.executescript(sql('schema.sql'))
        self.db.executescript(sql('sample_data.sql'))

    def tearDown(self):
        self.db.close()

    def test_schema_and_sample_data(self):
        tables = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables, {'users', 'categories', 'courses', 'materials'})
        self.assertEqual(self.db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM materials').fetchone()[0], 1)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_course_counts_include_zero(self):
        self.assertEqual(self.db.execute(sql('queries.sql')).fetchall(), [
            ('Database Systems', 0), ('Introduction to Programming', 1)])

    def test_duplicate_email_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO users (full_name, email, password_hash, role) VALUES ('Another', 'student@example.test', 'placeholder', 'student')")

    def insert_material(self, uploader=1, category=1, course=1, title='Title', size=1):
        self.db.execute('INSERT INTO materials (uploader_id, category_id, course_id, title, file_path, file_size_bytes) VALUES (?, ?, ?, ?, ?, ?)',
                        (uploader, category, course, title, 'placeholder', size))

    def test_blank_title_rejected(self):
        for title in ('', '   ', '\t\n'):
            with self.subTest(title=title), self.assertRaises(sqlite3.IntegrityError):
                self.insert_material(title=title)

    def test_invalid_foreign_keys_rejected(self):
        for field in ('uploader', 'category', 'course'):
            with self.subTest(field=field), self.assertRaises(sqlite3.IntegrityError):
                self.insert_material(**{field: 999})

    def test_file_size_boundaries(self):
        for size in (0, 52428801):
            with self.subTest(size=size), self.assertRaises(sqlite3.IntegrityError):
                self.insert_material(size=size)
        self.insert_material(size=52428800)

    def test_invalid_role_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO users (full_name, email, password_hash, role) VALUES ('Example', 'other@example.test', 'placeholder', 'guest')")


if __name__ == '__main__':
    unittest.main()
