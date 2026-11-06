# Frontend integration — 2026-11-06

Integrated the materials UI from `ibrashov/study-materials-exchange`, main commit
`1a05a17f64d636ea9304f31fcaf723f5bf07662f`, into the local Week 10 implementation.

`MaterialsPage`, `MaterialsSearchForm`, `MaterialList`, `useRequest`, formatting and
styles retain the teammate's search, category/course filters, pagination, retry,
timeout and stale-response handling. MaterialList also supports the local
authenticated PDF download. The existing `Materials.jsx` import remains an alias.

The shared API client combines the teammate's validated list responses and
camelCase-to-snake_case filters with local registration, login, upload and binary
downloads. Existing snake_case query fields and the second AbortSignal argument
remain accepted. ApiError exposes status, code and message for both feature sets.

The local backend already provides the required API shapes, so its routes and
database schema did not need changes. Authentication, upload and admin routes
remain implemented. The home page links to the shared materials view and keeps
the backend connection panel. The new search view retains the teammate's English
copy; existing EN/RU account, upload and navigation translations remain available.

## Run locally (PowerShell, from project root)

```powershell
.venv/Scripts/python.exe scripts/local_postgres.py start
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m backend.app.db.seed
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. The existing backend/.env holds local configuration;
frontend defaults to http://127.0.0.1:8000/api. PostgreSQL 17 and the existing
Python virtual environment are used by the local database helper.

## Verification

- JavaScript syntax checks and Python compileall passed.
- Vite production build passed.
- `npm test`: 30 passed (requires the API on port 8000).
- `npm run test:browser`: 20 passed, including the teammate's search UI tests and
  real registration → login → PDF upload → search → download, role restrictions,
  admin counts, account EN/RU switching and mobile layout.
- Python unittest discovery: 29 passed, including PostgreSQL integration.

Browser tests start their own API on 8001 and Vite on 5173. They require the
separate TEST_DATABASE_URL ending in `_test` and Microsoft Edge. Mock search
fixtures exist only in tests. No commit or push was made.
