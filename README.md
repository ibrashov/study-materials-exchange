# Study Materials Exchange

A Basics of Information Systems university project helping students find and share notes, presentations and course resources. Guests will browse/search; authenticated students will upload materials.

## TEAM MEMBERS: READ THIS BEFORE WRITING CODE

Read [TEAM_CONVENTIONS.md](docs/TEAM_CONVENTIONS.md) and [API_CONTRACT.md](docs/API_CONTRACT.md). Every member must follow the same field names, API paths, folder boundaries and configuration. Discuss proposed decisions before implementing them.

## Current stage

Week 10: a working React + Vite frontend and Python FastAPI skeleton communicate through GET /api/health. Loading, failure, retry and planned-module navigation are implemented and browser-tested. PostgreSQL is planned, not connected. No authentication, real material operations, storage, search or administration is implemented.

Week 9 achievements are preserved: four-table SQLite prototype, fictional sample metadata, course reporting query, ERD, requirements and seven database tests. SQLite is historical work, not the application's configured database. See [Week 9 progress](docs/TASK09_PROGRESS.md).

## Team

| Member | Role |
| --- | --- |
| Ibrashov Anuar | Project Manager & System Analyst: architecture, skeleton, contracts, conventions and coordination |
| Kozhakhmetov Talgat | Database & Backend: PostgreSQL, real operations and authentication |
| Ainakul Arnur | Admin Panel & Testing: admin, validation, roles and integration tests |
| Abylay Daryn | File Management & Search: storage, upload, search and download |
| Anuarbek Alibek | Frontend & Multilingual: login/registration, materials/upload UI and translations |

## Structure and stack

```text
frontend/        React 19 + Vite 7; src/api, components, pages, features, locales
backend/         FastAPI; app/api, schemas, models, services, db, core
database/       Week 9 SQLite scripts and ERD (preserved)
docs/           requirements, integration standards, architecture and progress
tests/          existing SQLite tests and new backend health tests
```

Detailed tree and ownership: [team guide](docs/TEAM_CONVENTIONS.md). Future PostgreSQL belongs to Talgat; file storage belongs to Daryn.

## Setup ? Windows PowerShell

Requirements: Python 3.12+ and Node.js 22.12+ (verified here with Python 3.14.3 and Node 24.13.1). Run from the repository root. Commands use npm.cmd to avoid PowerShell npm.ps1 execution-policy issues.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
cd frontend
npm.cmd ci
cd ..
```

If venv creation reports an ensurepip error but creates its Python executable (as in this environment), use the host pip to bootstrap dependencies into it:

```powershell
python -m pip --python .venv install -r backend/requirements.txt
```

Terminal 1, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, from the repository root:

```powershell
cd frontend
npm.cmd run dev
```

Frontend: http://127.0.0.1:5173 (also allowed CORS origin: http://localhost:5173).
Backend health: http://127.0.0.1:8000/api/health.
API documentation: http://127.0.0.1:8000/docs.

The backend root `/` has no page; use /docs or /api/health. Stop servers with Ctrl+C. Health returns `{"status":"ok","service":"study-materials-backend"}` and checks API availability only.

Backend .env is optional and loaded centrally. DATABASE_URL is empty and unused; no PostgreSQL installation is required. Frontend uses VITE_API_BASE_URL, defaulting to http://127.0.0.1:8000/api. Restart Vite after changing it. VITE values are public; never put credentials in them. Local origins are restricted and only GET is enabled cross-origin until future routes are integrated. .env, local databases, uploads, dependencies and caches are ignored; safe .env.example files are tracked.

## Verify before merging

From repository root, first run static validation:

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend tests
node --check frontend/src/api/client.js
node --check frontend/tests/client.test.js
node --check frontend/playwright.config.js
node --check frontend/browser-tests/connection.spec.js
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
python -m pip --python .venv check
```

With backend running on port 8000, from frontend/:

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run test:browser
npm.cmd audit
```

Browser tests require Microsoft Edge installed and port 5173 free; Playwright starts/stops Vite itself. They test actual CORS/HTTP communication, loading, blocked network errors, retry recovery and planned navigation. API-client tests use a real backend for the first test and controlled failures for negative tests. Build output is frontend/dist (ignored); `npm.cmd run preview` can preview it, but port 4173 must be explicitly added to CORS_ORIGINS to contact the backend.

Verified results: 10 Python tests, 2 API-client tests and 2 Edge browser tests passed; production build passed, dependency check passed, npm audit reported 0 vulnerabilities. See [verification details](docs/VERIFICATION.md) for environment limitations and exact results.

## Reference and next milestone

- [Requirements](docs/requirements.md), [ER diagram](database/ERD.md), [SQL schema](database/schema.sql), [database tests](tests/test_database.py)
- [Team conventions](docs/TEAM_CONVENTIONS.md), [API contract](docs/API_CONTRACT.md), [architecture](docs/ARCHITECTURE.md)
- [Anuar's Week 10 contribution and presentation](docs/WEEK10_ANUAR_PROGRESS.md), [complete changed-file list](docs/WEEK10_FILE_MANIFEST.md)

Week 11 plan: agree course selection/authentication decisions, integrate Talgat's PostgreSQL/authentication with Daryn's storage and Alibek's UI, and have Arnur test the first real vertical workflow. Search performance, production deployment, backups and restoration remain future work. Maximum file size remains 52,428,800 bytes; guest uploads remain forbidden. The skeleton demonstrates integration rather than completed feature delivery.

No commit or push was performed. Review changes and run the demo before committing manually. Suggested commit: `chore(architecture): add shared full-stack skeleton and team conventions`.
