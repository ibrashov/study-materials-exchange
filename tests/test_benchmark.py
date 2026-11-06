import importlib.util
from pathlib import Path
from sqlalchemy import text
from backend.app.main import app
from pg_base import PostgresCase

spec = importlib.util.spec_from_file_location('benchmark_search', Path('scripts/benchmark_search.py'))
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)

class Benchmark(PostgresCase):
    def test_reports_timing_and_removes_its_fixtures(self):
        report = benchmark.run(self.engine, self.client, rows=25, requests=5)
        self.assertEqual(report['rows'], 25)
        self.assertEqual(report['requests'], 5)
        self.assertGreater(report['p95_ms'], 0)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT count(*) FROM materials')), 0)

    def test_refuses_a_database_that_is_not_disposable(self):
        with self.assertRaises(SystemExit):
            benchmark.require_test_database('postgresql+psycopg://u:p@localhost/study_materials')
