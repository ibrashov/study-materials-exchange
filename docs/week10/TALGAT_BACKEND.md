# Talgat — database and backend

2026-11-05 · Kozhakhmetov Talgat · 24B031852.

**Implementation prepared by Codex. Personally verified by Talgat: pending.**

## Result and files

Real PostgreSQL configuration, canonical ORM models, Alembic migration, registration/login and shared session management are implemented. Files: backend/app/core/config.py; db/session.py and db/seed.py; models/entities.py; schemas/auth.py; services/auth.py; api/routes/auth.py; backend/migrations/versions/0001_week10.py; alembic.ini; backend/.env.example; scripts/local_postgres.py.

Run the root README PowerShell setup, then local_postgres.py start, alembic upgrade head and backend.app.db.seed. The optional local cluster uses 55432 and generated ignored credentials; an existing PostgreSQL connection may instead be configured. Never run automated tests against the development database.

## Explain the implementation

RegisterRequest trims the name and normalizes email; extra fields such as role fail validation. The register route constructs User with role='student' and hasher.hash(body.password), then db.commit(). SQLAlchemy's session writes to DATABASE_URL through psycopg. A unique email constraint catches duplicates; the route rolls back and returns 409. UserResponse exposes only user_id/full_name/email/role. Login verifies Argon2 and signs an expiring token; protected requests load the current user from PostgreSQL.

The four Week 9 table/column names are retained. PostgreSQL adds native integer typing, bounded strings, sequence-generated IDs, timezone-aware timestamps and FK indexes. Alembic adds a version bookkeeping table. Historical SQLite SQL/tests remain unchanged and are not imported into the runtime database. alembic check found no model drift.

## Demonstration and evidence

Start backend, open /docs, POST /api/auth/register with a new fictional example.com address and a 12+ character password. Expect 201. Run scripts/inspect_database.py to show the row and argon2_hash=True without revealing the hash. Repeat the email and expect 409. Demonstration credentials are supplied locally, not committed.

Executed evidence: TEST_REPORT.md PG01–PG05, PG09–PG11 and PG19 passed against PostgreSQL. Migration upgrade and drift check passed. Browser suite also registered real test users through HTTP. Development taxonomy has no seeded fictional student registrations.

## Personal review and Week 11

Talgat must trace register → session → INSERT → response, repeat 201/409 himself, inspect the migration and explain hashing versus encryption. Record date, commands and one personal improvement in this report before claiming personal contribution.

By 2026-11-13: add and execute one forward/backward migration test in a disposable database and one backup/restore exercise; deliver commands and restored-row evidence. Remaining: production least-privilege roles, account recovery, rate limiting and secret rotation.
