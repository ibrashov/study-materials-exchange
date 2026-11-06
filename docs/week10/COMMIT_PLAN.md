# Suggested review and commit groups

No commit or push has been made. The owner should inspect git diff and git status, then stage explicit paths manually. Use the actual author's Git identity; do not impersonate teammates. These groups describe feature ownership, not manual student authorship.

Because the router, schema, configuration, client and end-to-end tests are shared, the five commits are **ordered logical groups, not five independently deployable releases**. Shared integration files land in the last group; test/build the combined result. Do not use git add . without checking ignored/local data.

1. **feat(database): add PostgreSQL integration and registration**
   Stage backend/requirements.txt, backend/.env.example, .gitignore, alembic.ini, backend/migrations/, backend/app/db/, backend/app/models/, backend/app/schemas/auth.py, backend/app/services/auth.py, backend/app/api/routes/auth.py, scripts/local_postgres.py, scripts/inspect_database.py, docs/week10/TALGAT_BACKEND.md.
2. **feat(admin): add role checks and initial admin overview**
   Stage backend/app/api/dependencies.py, backend/app/api/routes/admin.py, frontend/src/features/admin/, docs/week10/ARNUR_ADMIN_TESTING.md.
3. **feat(materials): add PDF storage and material search**
   Stage backend/app/api/routes/materials.py, backend/app/schemas/materials.py, backend/app/services/storage.py, backend/app/services/README.md, docs/week10/DARYN_FILES_DATABASE.md.
4. **feat(frontend): add registration UI and initial styling**
   Stage frontend/src/App.jsx, frontend/src/pages/HomePage.jsx, frontend/src/features/auth/, frontend/src/features/materials/, frontend/src/locales/, frontend/src/styles.css, docs/week10/ALIBEK_FRONTEND.md.
5. **docs(integration): verify API contracts and team workflow**
   Stage backend/app/api/router.py, backend/app/core/config.py, backend/app/main.py, frontend/src/api/client.js, frontend/playwright.config.js, frontend/browser-tests/, tests/test_week10.py, scripts/browser_backend.py, README.md, docs/TEAM_CONVENTIONS.md, docs/API_CONTRACT.md, docs/ARCHITECTURE.md, docs/history/, docs/WEEK10_TEAM_STATUS.md, docs/WEEK10_DEMO_GUIDE.md, docs/week10/ANUAR_INTEGRATION.md, docs/week10/TEST_REPORT.md, docs/week10/FILE_MANIFEST.md, docs/week10/COMMIT_PLAN.md.

For each group, run git add -- followed by the separate quoted paths above (PowerShell supports normal double-quoted paths), inspect git diff --cached, then let the owner decide whether to commit. The final integration group contains code as well as documentation; the suggested message may be changed to feat(integration) if preferred.

Never stage backend/.env, .local-postgres/, uploads/, frontend/test-results/, tokens, user files, dependencies or build output. Historical database/*.sql and tests/test_database.py should remain unchanged. Before committing, run the README verification sequence and collect the five personal review records.
