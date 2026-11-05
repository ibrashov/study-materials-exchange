# TEAM CONVENTIONS ? official integration reference

All members must read this document and API_CONTRACT.md before adding code. Existing requirements and Week 9 schema remain the initial source of truth. New product decisions below are **Proposed ? Team Approval Required**; implementation of the skeleton does not imply team approval.

## Architecture and ownership

React + Vite calls FastAPI over HTTP. PostgreSQL and file storage are future integrations. The skeleton runs without either. SQLite scripts remain historical Week 9 work, not an active application database.

| Member | Owns | Integration dependency |
| --- | --- | --- |
| Anuar ? Project Manager & System Analyst | architecture, skeleton, contracts, naming, integration, documentation | coordinate contract changes with all owners |
| Talgat ? Database & Backend | PostgreSQL, schema, real operations, registration and authentication | agreed fields; no database connection at import time |
| Arnur ? Admin Panel & Testing | admin features, role/validation tests, integration testing, bugs | Talgat's server authorization |
| Daryn ? File Management & Search | storage, upload, search, download | Talgat's sessions and Alibek's forms |
| Alibek ? Frontend & Multilingual | login/registration UI, materials/upload UI, translations | central API client and agreed responses |

## Folder structure

```text
frontend/
  .env.example, package.json, package-lock.json, index.html
  src/
    api/client.js                 # shared HTTP boundary
    components/BackendStatus.jsx  # reusable connection panel
    pages/HomePage.jsx
    features/auth/               # Alibek
    features/materials/          # Alibek; coordinate with Daryn
    features/admin/              # Arnur
    locales/                     # Alibek
    App.jsx, main.jsx, styles.css
  tests/client.test.js
backend/
  .env.example, requirements.txt
  app/
    main.py                      # app and shared errors/CORS
    api/router.py                # /api prefix, register feature routers
    api/routes/health.py
    schemas/health.py            # public request/response schemas
    core/config.py               # shared environment settings
    models/                      # Talgat's future ORM models
    db/                          # Talgat's sessions/migrations
    services/                    # business logic; Daryn's storage/search
    __init__.py                  # packages also have initialization files
database/                       # preserved SQLite SQL and ERD
docs/                           # requirements, standards, progress
tests/                          # unittest database and backend tests
README.md, .gitignore
```

## Canonical fields

Do not rename existing columns. Tables are plural snake_case. Python modules, folders and fields use snake_case; React components use PascalCase `.jsx`, JS local variables may use camelCase. JSON always uses snake_case.

| Table | Existing columns |
| --- | --- |
| users | user_id, full_name, email, password_hash, role |
| materials | material_id, uploader_id, category_id, course_id, title, file_path, file_size_bytes, uploaded_at |
| categories | category_id, category_name, description, created_at |
| courses | course_id, course_name, course_code, description |

`password_hash` is internal only. `file_path` is internal storage metadata; expose a download endpoint instead of server filesystem paths. IDs are positive integers. Roles are `student` and `admin`; guest means unauthenticated, not a stored role. Never accept uploader_id or role from a registration/upload form as authority.

## API and JSON

Use `/api`, plural resource nouns, GET for reading and POST for creation; no action-like `/getMaterials`. Routes define HTTP behavior, schemas define public data, services implement work. Register each new router once in api/router.py. Do not add stubs that return successful fake operations.

Health example: `{"status":"ok","service":"study-materials-backend"}`.
Public user example: `{"user_id":1,"full_name":"Example Student","email":"student@example.test","role":"student"}`.
Error envelope: `{"error":{"code":"http_404","message":"Not Found"}}`. Implemented HTTP errors use `http_<status>`; validation errors use `validation_error`. Do not return secrets or raw request bodies in errors. Future services must map expected failures to safe HTTP errors; production logging/500 policy remains future work.

Proposed ? Team Approval Required: UTC ISO 8601 API timestamps, pagination, bearer token format, password policy and the detailed planned contract. SQLite historical timestamps are unchanged. GET must not change state. Never return password_hash.

## Authentication, authorization and uploads

Existing rules: guests may browse/search; only authenticated students upload. Server checks identity and permissions on every protected operation. Frontend visibility is not authorization. Admin operations require server-side admin checks; exact operations remain proposed. Password hashing and verification belong to Talgat; no authentication exists in the skeleton. Proposed bearer tokens use `Authorization: Bearer <token>`; token lifetime, persistence and refresh strategy require team/security review before implementation.

Actual file size must be 1?52,428,800 bytes (50 MB per existing requirement). Daryn validates streamed bytes, generated storage names, safe paths and file types; allowlist is Proposed ? Team Approval Required. Browser validation alone is insufficient. Derive uploader_id from identity. Coordinate database/file cleanup on failures; a SQL rollback does not remove a file.

The schema requires course_id, but requirements call course selection a proposed extension. Proposed ? Team Approval Required: require course_id in uploads to match the current schema. Resolve this before implementing uploads; never silently alter the schema or invent a default course.

## Configuration and startup

See root README for PowerShell commands. Frontend: `VITE_API_BASE_URL=http://127.0.0.1:8000/api`. Only public configuration belongs in VITE variables; never put secrets there. Restart Vite after environment changes. All frontend requests go through src/api/client.js. Handle non-2xx, invalid responses, loading, cancellation and network errors. Health checks API availability, not database readiness.

Backend reads backend/.env through core/config.py. CORS_ORIGINS is a JSON array limited by default to localhost/127.0.0.1 port 5173. Only GET is allowed cross-origin in this skeleton. When POST features arrive, Talgat must deliberately add methods/headers and test preflight. No wildcard origins. DATABASE_URL is optional and unused. Proposed future value shape: `postgresql+psycopg://<user>:<password>@localhost:5432/<database>`; never commit real values. Talgat will add driver, engine, sessions, migrations and rollback handling in db/, then inject sessions into services. No PostgreSQL schema or connection exists today.

## Adding a feature and merging

1. Read requirements and the contract; agree changes with affected owners. Mark unsettled decisions as proposed.
2. Create a branch such as `feat/talgat-auth`, `feat/daryn-storage`, `docs/anuar-contract`, or `fix/arnur-role-check` (proposed branch policy).
3. Keep changes inside the owned module; coordinate edits to shared router, config, client and dependencies with Anuar. Do not keep alternate copies of shared files.
4. Add real schemas/services/routes and UI states incrementally. Preserve canonical fields. Add migrations rather than editing historical SQLite SQL.
5. Run Python compile validation before unittest, and Node syntax checks before frontend tests/build. Add meaningful success and negative tests for new behavior. See README commands; frontend HTTP test needs a running backend.
6. Open a PR describing behavior, contract changes, test commands/results and limitations. Proposed ? Team Approval Required: one affected owner reviews before merge; no direct default-branch changes. Resolve conflicts on the feature branch, rerun affected checks, never force-push shared history.

Use conventional commits, e.g. `feat(auth): validate student registration`, `fix(storage): remove incomplete uploads`, `docs(api): clarify course requirement`. Never commit .env, tokens, node_modules, venvs, local uploads or database instances.

## Integration sequence

Anuar publishes and coordinates this foundation. Talgat first agrees database/auth interfaces and migrations. Daryn integrates storage, cleanup and search with those services. Alibek connects UI using the shared client and adds locales. Arnur tests guest/student/admin paths, validation and complete HTTP workflows. Anuar tracks unresolved contract decisions and integration regressions. Week 11 target: agree the course/auth contract, then demonstrate one real registration-to-upload vertical slice with the owners; this is a plan, not a completed feature.
