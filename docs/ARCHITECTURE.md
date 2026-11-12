# Architecture — Week 10 connected prototype

Week 11 adds a Render static frontend and FastAPI service, connected to shared Supabase PostgreSQL and a private Supabase Storage bucket. Local filesystem storage remains available for development. See [deployment](DEPLOYMENT.md) and [verification](WEEK11_ANUAR_SERVER.md).

Updated 2026-11-05. The original React/Vite shell, central client/router, health panel and error envelope are extended. Earlier architecture is preserved in history/week10-skeleton/ARCHITECTURE.md; Week 9 SQLite remains an independent historical test fixture.

~~~mermaid
flowchart LR
    Person[Guest / student / admin] --> UI[React pages and EN/RU labels]
    UI --> Client[Shared API client]
    Client -->|JSON / multipart + bearer| Router[FastAPI central router]
    Router --> Health[Health: API availability only]
    Router --> Auth[Registration / login / current user]
    Router --> Admin[Admin role check and counts]
    Router --> Materials[Materials / taxonomy / search / download]
    Auth --> Hash[Argon2id and signed JWT]
    Auth --> Session[Shared SQLAlchemy session]
    Admin --> Session
    Materials --> Session
    Session --> PG[(PostgreSQL: four canonical tables)]
    Materials --> Files[Bounded temporary PDF then safe local filename]
    Migration[Alembic 0001_week10] --> PG
    Legacy[Historical SQLite scripts] --> LegacyTests[Seven Week 9 tests]
~~~

All solid arrows describe implemented paths. The full browser registration/login/upload/search/download path was tested using the separate PostgreSQL test database, not SQLite. Development setup is also migrated and seeded; test accounts are distinguishable from developer-created registrations.

## Registration trace

AuthForm validates input, client.register sends POST /api/auth/register, the Pydantic schema trims/normalizes and rejects extra fields, the route hashes the password, and the shared SQLAlchemy session commits User to PostgreSQL. The unique email constraint catches duplicates, including concurrent inserts. UserResponse filters private fields before serialization. UI success appears only after a successful response.

Login verifies an Argon2 hash and signs a short-lived token. auth/me supplies the current public user. React keeps the token in memory. Protected backend dependencies validate the token and load the database user each time, so hiding a navigation item is never the access-control boundary.

## File trace

Student identity and category/course references are checked before application storage. Storage reads bounded chunks from FastAPI's multipart-spooled file, counts bytes, validates PDF structure, and renames a generated .part path. Metadata flush and response validation happen before commit. Failure triggers rollback and file deletion. PostgreSQL FK/check constraints reject invalid references and sizes. Search uses bound ORM expressions; downloads resolve a safe path and return attachment bytes.

Multipart parsing can spool bytes before application validation; no reverse-proxy body/rate limits or malware scanner are included. Abrupt process termination can orphan a file between rename and commit. A later reconciliation task is necessary before stronger reliability claims.

## Database evolution

The migration preserves canonical columns and four domain tables; Alembic adds its version bookkeeping table. PostgreSQL uses generated integer sequences, bounded strings, timezone-aware timestamps, native integer sizes, role/title/size checks and FK indexes. SQLite used TEXT timestamps, PRAGMA foreign_keys and a typeof integer check; PostgreSQL enforces integer column types directly. There is no automatic migration of fictional SQLite rows. No second active schema exists for file management.

## Local runtime and tests

Optional scripts/local_postgres.py starts a separate authenticated loopback PostgreSQL 17 instance at port 55432 with ignored credentials and data. Existing Windows service on 5432 is untouched. Normal API uses DATABASE_URL; tests require separate TEST_DATABASE_URL ending in _test. Browser tests run API 8001/Vite 5173; development API is 8000. Run test suites sequentially because they share the disposable test database.

Ownership: Talgat database/auth; Arnur admin/role checks; Daryn files/search/integrity; Alibek UI/translations; Anuar integration/contracts. These are review responsibilities for Codex-prepared implementation. Remaining concerns: personal review, backups, crash recovery, performance load, rate limiting, security/accessibility hardening and formal decision approval.
