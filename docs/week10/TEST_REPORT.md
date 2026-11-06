# Week 10 executed test report

Date: 2026-11-05 (Asia/Qyzylorda). Execution by Codex; personal student verification pending. Environment: Windows, Python 3.14.3, Node 24.13.1, PostgreSQL 17.6, Edge/Playwright. No PostgreSQL test used SQLite as a substitute.

## Baseline before implementation

- Original Python suite: 10/10 passed (seven historical SQLite, three health).
- Original client suite: 2/2 passed after starting the required HTTP backend.
- Original Edge suite: 2/2 passed after starting that backend.
- Original Vite build: passed.
- Initial sandbox Node spawning failed with EPERM; approved normal execution resolved it. Initial HTTP test failed with ECONNREFUSED while the backend was stopped; corrected setup then passed. These failed attempts are not concealed.

## Final executed results

| Check | Command (root unless noted) | Actual result |
| --- | --- | --- |
| Python syntax | .venv/Scripts/python.exe -m compileall -q backend tests scripts | Pass |
| Undefined names | .venv/Scripts/python.exe -m ruff check --select F821 backend tests scripts | Pass; ruff is an optional development tool |
| JS syntax | node --check on client.js, messages.js, week10.spec.js, playwright.config.js | Pass |
| Python suite | .venv/Scripts/python.exe -m unittest discover -s tests -v | 29 passed, no skips |
| Migration/model compatibility | .venv/Scripts/python.exe -m alembic check | No new upgrade operations detected |
| Dependency consistency | python -m pip --python .venv check | No broken requirements found |
| Client suite | frontend: npm.cmd test | 2 passed |
| Production frontend | frontend: npm.cmd run build | Passed, 32 modules transformed |
| Edge browser suite | frontend: npm.cmd run test:browser | 7 passed |
| Diff whitespace | git diff --check | Passed; Windows LF/CRLF notices only |

Python feature suite uses real PostgreSQL study_materials_test, migrated with Alembic. FastAPI TestClient exercises routing/auth/validation with sessions redirected to that database. Each test truncates only the four test-domain tables and uses temporary storage. The ordinary development database is not truncated. A missing test URL explicitly skips this suite, which must then be reported Not Run.

## Feature matrix

All IDs below refer to tests/test_week10.py and passed in the executed PostgreSQL suite.

| ID | Test method | Expected / actual outcome | Status |
| --- | --- | --- | --- |
| PG01 | test_registration_persists_and_hashes | 201; normalized row present; Argon2 verifies; no private fields | Pass |
| PG02 | test_missing_fields | 422 | Pass |
| PG03 | test_duplicate_normalized_email | 409 | Pass |
| PG04 | test_invalid_email | 422 | Pass |
| PG05 | test_role_injection_and_password_policy | extra role, short password, blank name rejected | Pass |
| PG06 | test_student_forbidden_admin | 403 | Pass |
| PG07 | test_admin_real_counts | 200 with actual counts 2 users/0 materials in fixture | Pass |
| PG08 | test_guest_admin_and_upload_denied | 401 | Pass |
| PG09 | test_invalid_expired_and_forged_tokens | 401 for invalid/expired/forged/deleted-user token | Pass |
| PG10 | test_login_wrong_password | 401 | Pass |
| PG11 | test_database_role_rechecked | prior admin token denied after DB role change | Pass |
| PG12 | test_pdf_upload_search_download | 201, matching saved/downloaded bytes, searches match, empty search [], guest download 401 | Pass |
| PG13 | test_invalid_pdf_empty_and_references_cleanup | 415/422, no files or metadata left | Pass |
| PG14 | test_oversized_actual_bytes | actual 52,428,801 bytes => 413, cleanup | Pass |
| PG15 | test_exact_storage_byte_boundary | 52,428,800 bytes accepted by storage counter | Pass; parser mocked only here |
| PG16 | test_database_failure_removes_saved_file | simulated commit IntegrityError => rollback/file cleanup | Pass; injected failure |
| PG17 | test_admin_cannot_upload | 403 | Pass |
| PG18 | test_postgres_keys_and_constraints | unique generated IDs; duplicate PK, invalid role/FKs and out-of-range size rejected | Pass |
| PG19 | test_cors_contract_and_taxonomy | POST Authorization preflight 200, real taxonomy, query bounds/OpenAPI routes | Pass |

PG15 is a focused byte-count test with PDF validation bypassed, not a claim that a valid 50 MB PDF was parsed. PG16 simulates a database failure while using real storage and PostgreSQL sessions. All other feature cases use actual validation and PostgreSQL. Historical SQLite tests remain separately labeled.

## Browser evidence

frontend/browser-tests/connection.spec.js preserves the two connection/retry checks; the planned-login assertion was updated to a real login form. week10.spec.js adds five scenarios:

1. Registration required fields/password matching, successful persistence and duplicate errors; EN/RU labels/errors.
2. Deliberately aborted registration network request produces a visible error (controlled negative case).
3. Actual browser registration, login, student denial from admin, upload, title search and PDF download.
4. Admin login and real overview counts.
5. Mobile layout at 390px without horizontal overflow.

Browser API runs on 8001 using TEST_DATABASE_URL; Vite is pointed at it. Test-only admin password is generated per run and not committed. Browser-generated student accounts use example.com addresses and are fixtures. Test downloads use the real stored PDF. Russian desktop/mobile screenshots in ignored frontend/test-results were visually inspected. A primary-button hover contrast defect was found and fixed.

## Issues resolved and limitations

Windows sandbox blocked subprocess spawning and temporary-file cleanup; suites passed with approved normal execution. The first new browser launch needed a quoted Windows executable path. Subsequent checks exposed select-label targeting and a test password regenerated in worker configuration; explicit accessible labels and one inherited random test password resolved them. No backend access controls were weakened.

Not executed: representative load test for the three-second target, malware scan, crash interruption recovery, backup/restore, production deployment, full accessibility audit, personally reviewed demonstrations. No claim of these passing. Normal exceptions are tested; sudden process/power failure is not atomic across PostgreSQL and the filesystem.

## Final follow-up on 2026-11-06

After the CSS hover correction, the production build and the two affected desktop-Russian/mobile browser checks passed again. The refreshed Russian screenshot was inspected and the button contrast was readable. Final static validation, migration drift check and git diff whitespace check passed. git check-ignore confirmed backend/.env, the local PostgreSQL data/password and uploads remain ignored; git diff showed no changes to the historical database files or SQLite tests. Read-only development-database inspection confirmed PostgreSQL 17.6 and no pre-seeded student/material rows.
