"""Repeatable fictional taxonomy; admin creation only via explicit local CLI."""
import argparse
from getpass import getpass
import os
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.orm import Session
from .session import engine_for
from ..core.config import settings
from ..models.entities import Category, Course, User
from ..schemas.auth import RegisterRequest
from ..services.auth import hasher

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admin', action='store_true')
    args = parser.parse_args()
    if not settings.database_url:
        parser.error('Set DATABASE_URL first')
    with Session(engine_for(settings.database_url)) as db:
        for name in ('Lecture Notes', 'Presentations', 'Assignments'):
            db.execute(insert(Category).values(category_name=name).on_conflict_do_nothing(index_elements=['category_name']))
        for code, name in [('PROG101', 'Introduction to Programming'), ('DB101', 'Database Systems'), ('BIS101', 'Basics of Information Systems')]:
            db.execute(insert(Course).values(course_code=code, course_name=name).on_conflict_do_nothing(index_elements=['course_code']))
        if args.admin:
            body = RegisterRequest(full_name='Local Demo Admin', email=os.environ.get('DEMO_ADMIN_EMAIL') or input('Demo admin email: '),
                                   password=os.environ.get('DEMO_ADMIN_PASSWORD') or getpass('Demo admin password (12+ characters): '))
            existing = db.scalar(select(User).where(User.email == str(body.email)))
            if existing and existing.role != 'admin':
                parser.error('Refusing to promote an existing student; choose a separate admin email')
            if not existing:
                db.add(User(full_name=body.full_name, email=str(body.email), password_hash=hasher.hash(body.password), role='admin'))
        db.commit()
    print('Development taxonomy seeded; no fictional students inserted.')
if __name__ == '__main__':
    main()
