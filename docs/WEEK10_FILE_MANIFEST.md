# Week 10 complete file manifest

Generated from git status after implementation. M = modified; A = new/untracked file ready for review. No files staged, committed or pushed.

| Change | File |
| --- | --- |
| M | `.gitignore` |
| M | `README.md` |
| A | `backend/.env.example` |
| A | `backend/__init__.py` |
| A | `backend/app/__init__.py` |
| A | `backend/app/api/__init__.py` |
| A | `backend/app/api/router.py` |
| A | `backend/app/api/routes/__init__.py` |
| A | `backend/app/api/routes/health.py` |
| A | `backend/app/core/__init__.py` |
| A | `backend/app/core/config.py` |
| A | `backend/app/db/README.md` |
| A | `backend/app/db/__init__.py` |
| A | `backend/app/main.py` |
| A | `backend/app/models/README.md` |
| A | `backend/app/models/__init__.py` |
| A | `backend/app/schemas/__init__.py` |
| A | `backend/app/schemas/health.py` |
| A | `backend/app/services/README.md` |
| A | `backend/app/services/__init__.py` |
| A | `backend/requirements.txt` |
| A | `docs/API_CONTRACT.md` |
| A | `docs/ARCHITECTURE.md` |
| A | `docs/TEAM_CONVENTIONS.md` |
| A | `docs/VERIFICATION.md` |
| A | `docs/WEEK10_ANUAR_PROGRESS.md` |
| A | `docs/WEEK10_FILE_MANIFEST.md` |
| A | `frontend/.env.example` |
| A | `frontend/browser-tests/connection.spec.js` |
| A | `frontend/index.html` |
| A | `frontend/package-lock.json` |
| A | `frontend/package.json` |
| A | `frontend/playwright.config.js` |
| A | `frontend/src/App.jsx` |
| A | `frontend/src/api/client.js` |
| A | `frontend/src/components/BackendStatus.jsx` |
| A | `frontend/src/features/admin/README.md` |
| A | `frontend/src/features/auth/README.md` |
| A | `frontend/src/features/materials/README.md` |
| A | `frontend/src/locales/README.md` |
| A | `frontend/src/main.jsx` |
| A | `frontend/src/pages/HomePage.jsx` |
| A | `frontend/src/styles.css` |
| A | `frontend/tests/client.test.js` |
| A | `tests/test_health.py` |

## Important file purposes

- backend/app/main.py: FastAPI setup, local CORS and shared error handling.
- backend/app/api/router.py and routes/health.py: central API registration and real health endpoint.
- backend/app/core/config.py and backend/.env.example: shared optional database/CORS settings.
- backend/app/schemas/health.py: typed response contract; package initialization files make imports explicit.
- backend/app/db, models and services: documented extension boundaries for future real operations.
- frontend/package.json and package-lock.json: repeatable React/Vite/Playwright dependencies and commands.
- frontend/src/api/client.js: configurable HTTP request and error helpers.
- frontend/src/components/BackendStatus.jsx: real status, loading, timeout, retry and errors.
- frontend/src/pages/HomePage.jsx, App.jsx, main.jsx, index.html and styles.css: reusable responsive application shell and planned navigation.
- frontend/src/features/*/README.md and locales/README.md: responsibilities for the next developers.
- tests/test_health.py, frontend/tests/client.test.js and browser-tests/connection.spec.js: backend, HTTP client and real browser checks.
- frontend/playwright.config.js: reproducible local Edge checks with a managed Vite server.
- docs/TEAM_CONVENTIONS.md: official naming, ownership, security and integration guide.
- docs/API_CONTRACT.md: implemented health contract and explicitly planned feature contracts.
- docs/ARCHITECTURE.md: implemented versus planned paths and Mermaid diagram.
- docs/WEEK10_ANUAR_PROGRESS.md: contribution evidence, disclosure and presentation script.
- docs/VERIFICATION.md: actual verification results and limitations.
- README.md: onboarding, setup, commands, current stage and links.
- .gitignore: preserves prior exclusions and allows safe environment templates; ignores browser outputs.

## Manual Git commands

Review the table above and run the commands in README. To include new files in your diff after review:

```powershell
git status --short
git add README.md .gitignore backend frontend docs tests/test_health.py
git diff --cached --stat
git diff --cached
git commit -m "chore(architecture): add shared full-stack skeleton and team conventions"
# Only after your own review; confirm current branch before choosing where to push:
git branch --show-current
git push
```

These are instructions only; the assistant did not stage, commit or push. Historical database files, requirements, Week 9 report and original database tests are unchanged.
