# Seven-minute Week 10 team demonstration

Prepared 2026-11-06. Scripts describe implemented behavior; students must inspect, test and adjust them personally. Say that Codex prepared the implementation and identify your own reviewed/improved work honestly.

## Preparation before the seven minutes

Follow README: start project PostgreSQL, migrate, seed taxonomy, start FastAPI 8000 and Vite 5173. Open website, /docs, editor and terminal. Prepare a small readable unencrypted PDF. Create a separate local admin using backend.app.db.seed --admin; enter credentials privately. Choose a fresh example.com student email. Do not display .env, access tokens or passwords on slides. Use scripts/inspect_database.py to show safe rows. Run tests before presenting and keep their actual output available; test database is separate from development.

## 0:00–1:00 — Anuar: architecture and integration

Say: “We already had a React and FastAPI skeleton. This week the shared API connects registration, PostgreSQL and file storage. One contract keeps our field names and routes consistent.”

Open docs/ARCHITECTURE.md diagram and API_CONTRACT.md. Show frontend/src/api/client.js and backend/app/api/router.py, then the live health panel. Expected: real API connected, mounted routes under /api. Show the recorded passing browser workflow result from TEST_REPORT.md.

Professor: “What did integration add beyond writing each feature?” Answer: “The same API client, router, field names, authentication headers and error shape let the modules exchange real data. The browser workflow tests that connection.”

## 1:00–2:00 — Talgat: registration and PostgreSQL

Say: “Registration validates the input, hashes the password and commits a user to PostgreSQL. The unique email constraint prevents duplicate accounts.”

In /docs POST /api/auth/register with a fresh example.com email, full name and a password entered locally. Expected 201 and public user fields. Run .venv/Scripts/python.exe scripts/inspect_database.py; expected row and argon2_hash=True. Repeat request; expected 409. Show routes/auth.py register and migration 0001_week10.

Professor: “Is the password encrypted?” Answer: “It is hashed with Argon2id. Login verifies the hash; the API never returns it.”

## 2:00–3:00 — Arnur: authorization and tests

Say: “The backend checks roles on every protected request. A student cannot access admin data even if they request the URL directly.”

Login in /docs as the student, use Authorize privately, GET /api/admin/overview: 403. Use the separate admin token: 200 with real counts. Show api/dependencies.py require_admin and tests/test_week10.py test_student_forbidden_admin/test_admin_real_counts. Keep the executed matrix open; no need to rerun the whole suite inside this minute.

Professor: “Would hiding the Admin button be enough?” Answer: “No. FastAPI must check the authenticated database user's role.”

## 3:00–4:00 — Daryn: files and constraints

Say: “The PDF bytes are stored locally. PostgreSQL stores the metadata and references to a user, category and course. Invalid references are rejected.”

In the website sign in as the student, choose Upload, supply a unique title, category/course and PDF. Expected “Material uploaded.” Show ignored uploads folder with generated filename and run inspect_database.py for the metadata. Show services/storage.py and the three FK columns in models/entities.py. Show PG18's passing invalid-FK evidence; do not insert invalid data into the normal development database.

Professor: “Does rolling back SQL remove a file?” Answer: “No. The application removes it on ordinary failure. Crash-orphan reconciliation is still a next task.”

## 4:00–5:00 — Alibek: frontend and languages

Say: “The forms call the real API and show validation or network errors. Core labels and common errors can switch between English and Russian.”

Sign out, open Registration, submit blank fields or mismatched passwords. Expected visible validation. Fill a second fresh email and submit; expected success only after 201. Switch EN/RU and show labels changing. Open features/auth/AuthForm.jsx and locales/messages.js. Avoid claiming every technical message is translated.

Professor: “Where does registration success come from?” Answer: “Only from a successful backend response after PostgreSQL commits the user.”

## 5:00–6:15 — Complete team workflow

Sign in as the earlier student, open Materials, search the uploaded title and download the PDF. Expected one matching material and actual downloaded bytes. Point out that listing/search work for guests but upload requires a student and download requires login. Refresh once if explaining that in-memory tokens intentionally log out on reload.

## 6:15–7:00 — Evidence, limits and next tasks

Show WEEK10_TEAM_STATUS.md and TEST_REPORT.md: 29 Python, 2 client, 7 Edge tests; build and migration check passed. Clearly identify PostgreSQL tests versus the historical SQLite suite and the two targeted mock cases.

Say: “This is our initial working prototype. Personal reviews and formal decisions are still being recorded. Next we will test migration and backup, add negative tests, check orphan files and search timing, improve accessibility, and verify setup on another Windows machine.”

If a live step fails, show its actual error and the last executed test evidence with its date. Do not narrate success or use fixture records as if a student had just registered. No manual student review has been recorded by this generated guide.
