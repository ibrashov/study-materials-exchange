# Week 10 team status — Study Materials Exchange

Generated 2026-11-06, Asia/Qyzylorda. Course: Basics of Information Systems. Final target: Week 15 working information system.

## Team status

The project has progressed from a health-connected skeleton to a small functional full-stack prototype. PostgreSQL migrations, real student registration/login, admin counts/permissions, PDF upload/storage/search/download and EN/RU forms are implemented. The complete workflow was exercised in Edge against a separate PostgreSQL test database. No fake material cards or fake database-success responses are used.

Week 9 SQLite schema/ERD/sample tests remain unchanged. The original Week 10 shell, router/client, health feature and conventions were extended, not recreated. Earlier document versions are preserved under history/week10-skeleton.

Evidence: 29 Python tests, 2 client tests and 7 browser tests passed; frontend build, Alembic model check and dependency consistency passed. See week10/TEST_REPORT.md for scopes, targeted mocks and initially failed attempts. Demonstrable: registration 201 then duplicate 409, persisted hashed user, student admin denial/admin count access, PDF saved and searchable, downloaded bytes and language switching.

Technical difficulties resolved: unknown credentials on existing PostgreSQL service (isolated project instance used), Windows sandbox process/temp restrictions, Windows browser command quoting, select labels and shared browser-test credentials. Remaining risks: formal decision approval, student review, crash-orphan files, load/performance target, backups, malware scanning and production security.

Next team milestone: by 2026-11-13, five personal reviews and a reproducible full demo on a second Windows machine, with recorded decisions and measured next-stage reliability work.

## Individual contributions and review assignments

**All implementation below was prepared by Codex. Personally verified by team member: NOT YET RECORDED for all five students.** These are artifacts to inspect and improve, not evidence of manual authorship. Each student should add date, command/output, explanation and a personal change before presenting it as their contribution.

| Student / ID | Responsibility and prepared feature | Files | Executed evidence | Required personal review |
| --- | --- | --- | --- | --- |
| Kozhakhmetov Talgat / 24B031852 | Database/backend: PostgreSQL, migration, registration/login | backend/app/db, models/entities.py, schemas/auth.py, services/auth.py, routes/auth.py, backend/migrations | PG01–05, PG09–11; migration/drift check | Trace INSERT/commit, hash verification, email constraint; repeat 201/409 |
| Ibrashov Anuar / 24B031812 | PM/analyst: extend existing integration, contract, CORS, coordinated evidence | router.py, main.py, config.py, frontend/src/api/client.js, docs, scripts/browser_backend.py | PG19; client tests; complete Edge workflow | Compare each route/field with contract; run on second machine; collect reviews |
| Ainakul Arnur / 24B031609 | Admin/testing: role dependencies, real counts, admin UI | api/dependencies.py, routes/admin.py, features/admin/AdminPage.jsx, tests/test_week10.py | PG02–11/17 and Edge admin/student checks | Repeat guest/student/admin cases and explain backend enforcement |
| Abylay Daryn / 24B031598 | Files/search: bounded PDF storage, metadata, search/download, PK/FKs | services/storage.py, routes/materials.py, schemas/materials.py, shared model/migration | PG12–19; browser upload/search/download | Trace file versus row transaction; test invalid FK and cleanup |
| Anuarbek Alibek / 24B031648 | Frontend/languages: forms, API states, EN/RU and compact UI | App.jsx, HomePage.jsx, features/auth/materials, locales/messages.js, styles.css | Build; browser validation/language/mobile/network cases | Trace forms/client, keyboard use, both languages and error states |

## Measurable Week 11 tasks

Suggested deadline for each: **2026-11-13** (team may adjust to the actual course schedule).

| Student | Next task | Expected deliverable |
| --- | --- | --- |
| Talgat | Execute forward/backward migration and one backup/restore exercise in disposable databases | Commands, restored row evidence and a passing migration test |
| Anuar | Collect five dated reviews, record course/PDF/download/token decisions, run second-machine setup | Five review entries, decision log, setup/workflow evidence |
| Arnur | Add and run five negative/regression tests including encrypted PDF and missing file | Personally executed matrix with expected/actual results |
| Daryn | Add read-only orphan-file report; benchmark search over 1,000 labeled fixture materials | Reconciliation output and p95 timing versus 3-second target |
| Alibek | Translate remaining health messages and keyboard-test all five feature views | Three verified UI improvements and desktop/mobile screenshots |

## Honest completion boundary

Implemented and tested: the requested minimum connected workflow and admin checks. Pending: each teammate's own inspection, review, demonstration and improvement. Proposed prototype decisions (not claimed approved): required course, PDF-only, authenticated downloads, token lifetime/storage. Guest download is not enabled. No production readiness, full security audit, representative performance success or manual student contribution is claimed.

Detailed reports: [Talgat](week10/TALGAT_BACKEND.md), [Anuar](week10/ANUAR_INTEGRATION.md), [Arnur](week10/ARNUR_ADMIN_TESTING.md), [Daryn](week10/DARYN_FILES_DATABASE.md), [Alibek](week10/ALIBEK_FRONTEND.md). Use [demo guide](WEEK10_DEMO_GUIDE.md) after personal review. No commit/push/PR/issues were created automatically.
