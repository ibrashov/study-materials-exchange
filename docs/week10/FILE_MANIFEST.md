# Week 10 implementation file manifest

Generated 2026-11-06. No files were committed or pushed. Review git status --short and git diff for the current working tree.

## Added application files

- alembic.ini
- backend/migrations/env.py, script.py.mako, versions/0001_week10.py
- backend/app/db/session.py, seed.py
- backend/app/models/entities.py
- backend/app/schemas/auth.py, materials.py
- backend/app/services/auth.py, storage.py
- backend/app/api/dependencies.py
- backend/app/api/routes/auth.py, admin.py, materials.py
- frontend/src/features/auth/AuthForm.jsx
- frontend/src/features/admin/AdminPage.jsx
- frontend/src/features/materials/Materials.jsx, UploadForm.jsx
- frontend/src/locales/messages.js
- scripts/local_postgres.py, inspect_database.py, browser_backend.py
- tests/test_week10.py
- frontend/browser-tests/week10.spec.js

## Changed existing application/configuration files

- .gitignore — ignore project-local database/runtime secrets
- backend/.env.example, backend/requirements.txt
- backend/app/core/config.py, backend/app/main.py, backend/app/api/router.py
- frontend/src/api/client.js — extended existing shared client
- frontend/src/App.jsx, frontend/src/pages/HomePage.jsx, frontend/src/styles.css
- frontend/playwright.config.js, frontend/browser-tests/connection.spec.js
- Module READMEs in backend/app/db, models, services and frontend/src/features/auth, materials, admin, locales

## Documentation

Updated README.md, docs/TEAM_CONVENTIONS.md, API_CONTRACT.md and ARCHITECTURE.md. Added exact pre-feature copies in docs/history/week10-skeleton/. Relative links inside those archived documents are historical snapshots; use current root documentation for navigation.

Added docs/WEEK10_TEAM_STATUS.md, docs/WEEK10_DEMO_GUIDE.md and docs/week10/TALGAT_BACKEND.md, ARNUR_ADMIN_TESTING.md, DARYN_FILES_DATABASE.md, ALIBEK_FRONTEND.md, ANUAR_INTEGRATION.md, TEST_REPORT.md, COMMIT_PLAN.md and this manifest.

## Preserved work

Historical database/schema.sql, ERD.md, sample_data.sql, queries.sql, tests/test_database.py and earlier progress/verification documents remain unchanged. Health route/schema/tests and BackendStatus.jsx remain intact. Existing React entrypoint, dependency manifest/lockfile and package layout remain intact. No reset, history rewrite, duplicate service or replacement frontend was made.

## Ignored local outputs — never stage

backend/.env; .local-postgres/ (generated database password/data/logs and browser upload fixtures); uploads/; frontend/test-results/ screenshots; frontend/dist/; .venv/ and node_modules/. These are local runtime/test artifacts, not student-authored source evidence.
