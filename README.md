# Study Materials Exchange

Week 11 cloud deployment: [website](https://study-materials-web.onrender.com/), [API health](https://study-materials-api-v15q.onrender.com/api/health), [deployment guide](docs/DEPLOYMENT.md) and [verification report](docs/WEEK11_ANUAR_SERVER.md). The free backend may take a minute to wake after inactivity.

Basics of Information Systems university project. Updated 2026-11-06.

Read [team conventions](docs/TEAM_CONVENTIONS.md), [API contract](docs/API_CONTRACT.md), and [team status](docs/WEEK10_TEAM_STATUS.md) first.

## Current stage

The system works end to end on PostgreSQL: registration, login, role checks, PDF upload, search, authenticated download, an admin panel with user management, course and download reports, verified backups and full English/Russian UI. See [project status](docs/PROJECT_STATUS.md) for each item checked against the Task 9 guide, and what is not done.

Historical work is preserved: Week 9 SQLite schema, ERD, sample data and seven tests are unchanged; the original health endpoint, shared router/client, shell and connection panel remain. Pre-feature versions of the four integration documents are in [history/week10-skeleton](docs/history/week10-skeleton). Earlier evidence remains in [VERIFICATION.md](docs/VERIFICATION.md) and [WEEK10_ANUAR_PROGRESS.md](docs/WEEK10_ANUAR_PROGRESS.md).

## Team and ownership

| Member | ID | Week 10 area |
| --- | --- | --- |
| Kozhakhmetov Talgat | 24B031852 | PostgreSQL, migrations, registration/login |
| Ibrashov Anuar | 24B031812 | Existing foundation, contracts, integration and coordination |
| Ainakul Arnur | 24B031609 | Admin API/UI, role and validation tests |
| Abylay Daryn | 24B031598 | Storage/search/download, database integrity |
| Anuarbek Alibek | 24B031648 | Forms, styling and EN/RU labels |

This implementation was prepared by Codex. No teammate's personal authorship, review or verification is claimed. Each student must review and test their area before presenting it.

## macOS or Linux setup

Requirements: Python 3.12+, Node 22.12+, PostgreSQL 17 and Google Chrome for browser tests.

~~~bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp frontend/.env.example frontend/.env
(cd frontend && npm ci)
.venv/bin/python scripts/local_postgres.py start
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m backend.app.db.seed
.venv/bin/python -m backend.app.db.seed --admin   # optional demo admin, asks for email and password
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
~~~

In a second terminal run `cd frontend && npm run dev`, then open http://127.0.0.1:5173. Homebrew and standard Linux PostgreSQL locations are found automatically; otherwise set PG_BIN.

## Windows PowerShell setup

Requirements: Python 3.12+, Node 22.12+, PostgreSQL 17 binaries. Verified with Python 3.14.3, Node 24.13.1 and PostgreSQL 17.6. Microsoft Edge is used by browser tests. No Docker or cloud account is required.

Run from the repository root:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
# If this environment's venv lacks pip, use the host pip instead:
python -m pip --python .venv install -r backend/requirements.txt
Copy-Item frontend/.env.example frontend/.env
cd frontend
npm.cmd ci
cd ..
~~~

Choose one PostgreSQL setup:

1. **Automatic project-local instance (configured in this workspace):** the command below uses installed PostgreSQL binaries, starts a separate server on 127.0.0.1:55432, creates study_materials and study_materials_test, and generates ignored backend/.env credentials. It preserves any existing backend/.env and does not modify the Windows PostgreSQL service. It uses a local development superuser; do not deploy this account.

~~~powershell
# Set PG_BIN only if PostgreSQL binaries are elsewhere:
# $env:PG_BIN = 'C:\Program Files\PostgreSQL\17\bin'
.\.venv\Scripts\python.exe scripts/local_postgres.py start
~~~

2. **Your existing PostgreSQL service:** create separate development and disposable test databases using a local account you control. Copy backend/.env.example to backend/.env only if that file does not exist. Set DATABASE_URL, TEST_DATABASE_URL (database name must end in _test) and a random AUTH_SECRET of at least 32 characters. Use postgresql+psycopg URLs and URL-encode special characters in credentials. Do not paste passwords into chat or commit them. Never point tests at the development database.

Then migrate and seed:

~~~powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.app.db.seed
# Optional separate local demo admin; prompts for email and hidden password:
.\.venv\Scripts\python.exe -m backend.app.db.seed --admin
~~~

Seeding is repeatable and inserts only fictional category/course examples. The admin command does not promote an existing student or reset an existing admin password. DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD may alternatively be supplied in the local environment; never commit them.

Terminal 1, repository root:

~~~powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
~~~

Terminal 2:

~~~powershell
cd frontend
npm.cmd run dev
~~~

Open http://127.0.0.1:5173. Choose Registration, enter name/email and matching 12–128-character passwords, then sign in. Upload a readable PDF with a category and course; search its title on Materials. Admin navigation appears after signing in with a CLI-created admin.

FastAPI docs: http://127.0.0.1:8000/docs. Health: /api/health reports API availability only. The backend root / has no webpage. To inspect actual rows without displaying password hashes:

~~~powershell
.\.venv\Scripts\python.exe scripts/inspect_database.py
~~~

Stop application servers with Ctrl+C. Stop the optional project database with:

~~~powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py stop
~~~

## Verification

Run Python tests before browser tests; both use the separate test database. Python tests truncate the four canonical tables in that database. Do not run them concurrently with a browser demo using that database.

~~~powershell
.\.venv\Scripts\python.exe -m compileall -q backend tests scripts
node --check frontend/src/api/client.js
node --check frontend/src/locales/messages.js
node --check frontend/browser-tests/week10.spec.js
node --check frontend/playwright.config.js
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m alembic check
python -m pip --python .venv check
# With the development backend running on port 8000:
cd frontend
npm.cmd test
npm.cmd run build
npm.cmd run test:browser
~~~

Browser tests start their own backend on 8001 and Vite on 5173 and stop them afterwards; keep these ports free. That backend requires TEST_DATABASE_URL, seeds taxonomy and creates a test-only admin with a random run-specific password. Test upload bytes live in ignored .local-postgres/browser-uploads. The test-only launcher is not a development server. If TEST_DATABASE_URL is missing, Python PostgreSQL tests are explicitly skipped; browser tests fail instead of silently using SQLite.

Latest results are in [project status](docs/PROJECT_STATUS.md). Browser tests use Edge on Windows and Chrome elsewhere; set PLAYWRIGHT_CHANNEL to override.

## Backups

`scripts/backup.py` backs up the database and files, checks them and proves they restore. See [backup and restore](docs/BACKUP_RESTORE.md).

## Prototype decisions and remaining work

Week 10 proposed decisions implemented consistently: PDF-only uploads; required course; authenticated downloads; HS256 tokens valid 60 minutes; tokens only in React memory (refresh logs out); lowercase trimmed emails; 12–128-character passwords. Public registration always creates students. The backend checks roles on every protected request.

Remaining work is listed in [project status](docs/PROJECT_STATUS.md).

See [seven-minute demo](docs/WEEK10_DEMO_GUIDE.md), [team status and Week 11 tasks](docs/WEEK10_TEAM_STATUS.md), [five role reports](docs/week10), and [suggested commit groups](docs/week10/COMMIT_PLAN.md). No commit, push, PR or issue was created.
