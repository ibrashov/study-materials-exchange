"""Times materials search over labelled fixture rows in the disposable test database only."""
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import delete, insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from backend.app.models.entities import Category, Course, Material, User

TARGET_MS = 3000
QUERIES = ({'q': 'fixture'}, {'q': 'week 7'}, {'q': 'benchmark course'}, {'q': 'no such material'}, {'limit': 100}, {'offset': 500})

def require_test_database(url):
    if not (make_url(url).database or '').endswith('_test'):
        raise SystemExit('Refusing to benchmark outside a *_test database')

def run(engine, client, rows=1000, requests=200):
    with Session(engine) as db:
        user = User(full_name='Benchmark Fixture', email='benchmark-fixture@example.com', password_hash='not-a-hash', role='student')
        category = Category(category_name='[benchmark fixture]')
        course = Course(course_code='BENCHFIX', course_name='Benchmark Course')
        db.add_all([user, category, course])
        db.commit()
        ids = user.user_id, category.category_id, course.course_id
        try:
            db.execute(insert(Material), [{'uploader_id': ids[0], 'category_id': ids[1], 'course_id': ids[2],
                                           'title': f'[fixture] Week {index % 15} summary {index}',
                                           'file_path': f'fixture-{index}.pdf', 'file_size_bytes': 1024} for index in range(rows)])
            db.commit()
            timings = []
            for index in range(requests):
                started = time.perf_counter()
                response = client.get('/api/materials', params={**QUERIES[index % len(QUERIES)], 'category_id': ids[1]})
                timings.append((time.perf_counter() - started) * 1000)
                response.raise_for_status()
        finally:
            db.rollback()
            db.execute(delete(Material).where(Material.uploader_id == ids[0]))
            db.execute(delete(User).where(User.user_id == ids[0]))
            db.execute(delete(Category).where(Category.category_id == ids[1]))
            db.execute(delete(Course).where(Course.course_id == ids[2]))
            db.commit()
    timings.sort()
    p95 = timings[max(0, int(len(timings) * 0.95) - 1)]
    return {'rows': rows, 'requests': requests, 'p50_ms': round(statistics.median(timings), 2), 'p95_ms': round(p95, 2),
            'max_ms': round(timings[-1], 2), 'target_ms': TARGET_MS, 'passed': p95 < TARGET_MS}

def main():
    from fastapi.testclient import TestClient
    from backend.app.core.config import settings
    from backend.app.db.session import engine_for, get_db
    from backend.app.main import app
    url = settings.test_database_url
    if not url:
        raise SystemExit('Set TEST_DATABASE_URL first')
    require_test_database(url)
    engine = engine_for(url)
    def test_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        print(json.dumps(run(engine, client)))

if __name__ == '__main__':
    main()
