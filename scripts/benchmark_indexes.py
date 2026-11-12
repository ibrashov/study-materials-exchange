"""Week 11 (Daryn): benchmark /api/materials search over labelled fixture rows.

Runs against a DISPOSABLE database only (name must end in _test or _bench). It creates
fixture rows (titles start with 'BENCH-'), times the real SQL used by the endpoint through
the FastAPI app, with and without the Week 11 indexes, and prints p50/p95 in milliseconds.

    .venv/bin/python scripts/benchmark_indexes.py --rows 10000 --runs 60
"""
import argparse
import os
from pathlib import Path
import random
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

TARGET_MS = 3000
WORDS = ['linked', 'lists', 'normalization', 'sql', 'joins', 'recursion', 'graphs', 'sorting', 'networks',
         'security', 'requirements', 'uml', 'testing', 'python', 'react', 'http', 'index', 'transactions']
INDEXES = {
    'ix_materials_title_trgm': "CREATE INDEX ix_materials_title_trgm ON materials USING gin (title gin_trgm_ops)",
    'ix_materials_course_newest': "CREATE INDEX ix_materials_course_newest ON materials (course_id, material_id DESC)",
    'ix_materials_category_newest': "CREATE INDEX ix_materials_category_newest ON materials (category_id, material_id DESC)",
}

def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', type=int, default=10000)
    parser.add_argument('--runs', type=int, default=60)
    args = parser.parse_args()
    from backend.app.core.config import settings
    url = settings.test_database_url
    if not url or not (make_url(url).database or '').endswith(('_test', '_bench')):
        raise SystemExit('TEST_DATABASE_URL (database name ending in _test or _bench) is required')
    settings.database_url = url
    settings.rate_limit_enabled = False
    from backend.app.db.session import engine_for
    from backend.app.main import app
    from alembic import command
    from alembic.config import Config
    os.chdir(Path(__file__).resolve().parents[1])
    command.upgrade(Config('alembic.ini'), 'head')
    engine = engine_for(url)
    rng = random.Random(11)
    with engine.begin() as c:
        c.execute(text("DELETE FROM materials WHERE title LIKE 'BENCH-%'"))
        c.execute(text("INSERT INTO categories(category_name) VALUES ('Lecture Notes'),('Presentations'),('Assignments') ON CONFLICT DO NOTHING"))
        for code, name in [('PROG101', 'Introduction to Programming'), ('DB101', 'Database Systems'), ('BIS101', 'Basics of Information Systems')]:
            c.execute(text('INSERT INTO courses(course_code, course_name) VALUES (:a,:b) ON CONFLICT DO NOTHING'), {'a': code, 'b': name})
        c.execute(text("INSERT INTO users(full_name,email,password_hash,role) VALUES ('Bench','bench@example.com','x','student') ON CONFLICT DO NOTHING"))
        uid = c.execute(text("SELECT user_id FROM users WHERE email='bench@example.com'")).scalar_one()
        cats = [r[0] for r in c.execute(text('SELECT category_id FROM categories'))]
        crs = [r[0] for r in c.execute(text('SELECT course_id FROM courses'))]
        rows = [{'u': uid, 'c': rng.choice(cats), 'k': rng.choice(crs), 't': f"BENCH-{i} " + ' '.join(rng.sample(WORDS, 3)),
                 'p': f'bench-{i}.pdf', 's': rng.randint(1000, 5_000_000)} for i in range(args.rows)]
        c.execute(text('INSERT INTO materials(uploader_id,category_id,course_id,title,file_path,file_size_bytes) VALUES (:u,:c,:k,:t,:p,:s)'), rows)
        c.execute(text('ANALYZE materials'))
    client = TestClient(app)
    queries = [{'q': 'normalization'}, {'q': 'sql joins'}, {'q': 'Database'}, {'q': 'BENCH-77'}, {'q': 'BENCH-123456'}, {'q': 'zzqx'}, {},
               {'category_id': cats[0]}, {'course_id': crs[0], 'q': 'graphs'}]
    def measure(label):
        timings = []
        for _ in range(args.runs):
            for params in queries:
                t = time.perf_counter()
                r = client.get('/api/materials', params={**params, 'limit': 20})
                timings.append((time.perf_counter() - t) * 1000)
                assert r.status_code == 200, r.text
        p50, p95 = statistics.median(timings), percentile(timings, 95)
        print(f'{label:<28} n={len(timings):<5} p50={p50:7.2f} ms  p95={p95:7.2f} ms  max={max(timings):7.2f} ms')
        return p95
    print(f'Rows: {args.rows} BENCH fixtures; target p95 < {TARGET_MS} ms')
    with engine.begin() as c:
        for name in INDEXES:
            c.execute(text(f'DROP INDEX IF EXISTS {name}'))
        c.execute(text('ANALYZE materials'))
    before = measure('without Week 11 indexes')
    with engine.begin() as c:
        for ddl in INDEXES.values():
            c.execute(text(ddl))
        c.execute(text('ANALYZE materials'))
    after = measure('with Week 11 indexes')
    print(f'p95 improvement: {before / after:.1f}x; target {"MET" if after < TARGET_MS else "NOT MET"}')
    with engine.begin() as c:
        print('\nEXPLAIN (title search):')
        for row in c.execute(text("EXPLAIN SELECT * FROM materials WHERE title ILIKE '%normalization%' ORDER BY material_id DESC LIMIT 20")):
            print('  ' + row[0])
        c.execute(text("DELETE FROM materials WHERE title LIKE 'BENCH-%'"))
    print('\nFixtures removed.')

if __name__ == '__main__':
    main()
