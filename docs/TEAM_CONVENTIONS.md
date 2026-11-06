# Team conventions — Week 10 functional extension

Updated 2026-11-05. The original skeleton conventions are preserved in history/week10-skeleton/TEAM_CONVENTIONS.md. Week 9 requirements and canonical names remain in force. Implementation prepared by Codex; student review is pending.

## Boundaries and ownership

React calls frontend/src/api/client.js; feature code must not create a second HTTP client. FastAPI feature routers are mounted once through backend/app/api/router.py. Configuration lives in core/config.py; all database sessions come from db/session.py. Models are in models/entities.py; there is one Alembic migration history under backend/migrations. Historical database/*.sql is SQLite evidence, never the runtime database.

| Owner | Modules | Shared review |
| --- | --- | --- |
| Talgat | db/session.py, db/seed.py, models, schemas/auth.py, services/auth.py, routes/auth.py, migrations | Daryn verifies keys; Anuar verifies contract |
| Arnur | routes/admin.py, api/dependencies.py, AdminPage.jsx, role/validation tests | Talgat reviews authentication |
| Daryn | services/storage.py, routes/materials.py, schemas/materials.py, integrity tests | Talgat shares models/session |
| Alibek | AuthForm, Materials, UploadForm, App, HomePage, styles, locales | all requests through shared client |
| Anuar | router/main/config integration, API client, HTTP/browser integration, documents | coordinate all shared changes |

Ownership is an assignment for review and future work, not a claim of manual authorship.

## Canonical fields and responses

Tables: users, categories, courses, materials. Columns keep the Week 9 names, including user_id, material_id, uploader_id, category_id, course_id, full_name, email, password_hash, role, title, file_path, file_size_bytes and uploaded_at. JSON is snake_case. Python uses snake_case; React components use PascalCase; local JS variables may be camelCase.

Never expose password_hash or file_path through public responses. Do not trust frontend role/uploader_id. Registration forbids extra JSON fields; upload ignores extra metadata and always derives uploader_id from the authenticated database user. Roles are student/admin. Guest is an unauthenticated state.

Error envelope: {"error":{"code":"http_409","message":"Email is already registered"}}. Validation uses validation_error and a safe generic message. Database/storage errors return safe 503 messages, not connection strings or paths. Health checks API availability only.

## Week 10 proposed decisions used by the prototype

These are reasonable implementation choices authorized for this prototype, **not recorded team approval**:

- PDF only: nonempty, at most 52,428,800 actual bytes, PDF header and parser validation, unencrypted and at least one page. This is new in Week 10. Browser extension checks are convenience only; backend validation is authoritative.
- course_id is required to match the existing four-table schema. The earlier requirements call course selection proposed; no automatic default course is invented.
- Guests browse/search; only students upload. Admins do not gain student upload privileges. Downloads require an authenticated student or admin; public downloads remain unapproved.
- Passwords are 12–128 characters and hashed with Argon2id. Names are trimmed (1–120 characters). Email is trimmed/lowercased, validated and limited to 254 characters; the database unique constraint resolves races.
- JWT HS256 with configured random secret (32+ characters), issuer, audience, subject, issued-at and expiration. Default lifetime is 60 minutes (configurable 1–1440). Roles are read from PostgreSQL, not token claims. No refresh token/revocation list yet.
- Browser tokens exist only in React memory and disappear on refresh/logout. This limits persistence but does not protect against script injection while signed in. Logout clears browser state; a previously copied token remains valid until expiry. No secrets in VITE values.
- Timestamps use PostgreSQL timezone-aware columns and API ISO 8601 values. The local PostgreSQL session may emit a timezone offset; consumers must parse the offset, not assume a trailing Z.
- Listing has limit 1–100 (default 20), offset >=0, case-insensitive literal substring search over title/course/category, and optional positive course/category filters.

## Storage and configuration

Uploads use generated UUID filenames in UPLOADS_DIR (default repository/uploads). Save bounded chunks to .part, parse PDF, rename, flush metadata, then commit. Application failures roll back and remove files. Abrupt process termination between file rename and commit can still leave an orphan; reconciliation is Week 11 work. Do not place uploads in a static public directory. Download paths must remain directly under the resolved upload directory.

DATABASE_URL uses postgresql+psycopg. Engine creation is lazy; no database connection is made at app import. AUTH_SECRET is required for login/protected endpoints. TEST_DATABASE_URL must be a distinct disposable database ending in _test. Test fixtures must be labeled and never presented as real student registrations.

CORS allows explicit localhost/127.0.0.1:5173 origins, GET/POST and Content-Type/Authorization; credentials mode is false. Add preview origins explicitly when needed. .env, .local-postgres, uploads, caches and build output are ignored. Safe .env.example is tracked.

## Working together

Use the current API_CONTRACT.md. Discuss changes with affected owners and preserve the schema history. Run syntax/static checks before tests, then meaningful negative/API/browser checks. Do not use development data for automated tests. Keep generated work distinct from personal review evidence. Suggested commit groups are in week10/COMMIT_PLAN.md; the owner reviews and commits manually. No automated push, PR, issue, history rewrite or teammate impersonation.
