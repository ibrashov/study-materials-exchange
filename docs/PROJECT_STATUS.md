# Project status — 2026-11-06

Checks every item the Task 9 defense guide listed as unfinished against the current code. Week 10 and later implementation was AI-assisted. Personal review by each student is still pending and is not claimed here.

## Items from the guide

| Guide item | Status | Where |
| --- | --- | --- |
| Registration and login | Done | `routes/auth.py`, `features/auth` |
| Access control, least privilege | Done, enforced on the server | `api/dependencies.py` |
| Upload with validation | Done | `routes/materials.py`, `services/storage.py` |
| Failed upload leaves no file or row | Done for normal failures | same, tests PG13–16 |
| Crash leaves files and rows out of step | Detected and cleanable | `services/reconcile.py`, admin panel |
| Website search and filters | Done | `features/materials` |
| Download | Done for signed-in users | `routes/materials.py` |
| Admin panel | Done: users, block, roles, categories, courses, moderation | `features/admin` |
| Course count report and its business decision | Done: courses with fewest materials first | `/api/admin/reports/courses` |
| Download statistics and popularity | Done | `/api/admin/reports/downloads` |
| Automatic backup and restore testing | Done as tooling; the schedule must be installed on the host | `docs/BACKUP_RESTORE.md` |
| English and Russian | Done for all interface text | `locales/messages.js` |

## Week 11 tasks from the team status

| Task | Result |
| --- | --- |
| Forward and backward migration, backup and restore exercise | Done, `tests/test_migrations.py`, `tests/test_backup.py` |
| Five negative tests, including encrypted PDF and missing file | Done, `tests/test_admin_features.py` |
| Orphan-file report | Done, `scripts/reconcile_storage.py` |
| Search benchmark over 1,000 labelled rows | Done, `scripts/benchmark_search.py` |
| Translate health messages, keyboard check | Done, `browser-tests/complete.spec.js` |
| Decision log | Listed below; team approval is not recorded |
| Five personal reviews, second-machine setup | **Not done: only each student can do this** |

## Results on macOS

Python 3.12.13, Node 26.0.0, PostgreSQL 17.9, Chrome 157.

| Check | Result |
| --- | --- |
| Python tests with PostgreSQL | 75 passed |
| API client and unit tests | 44 passed |
| Browser tests, real API and PostgreSQL | 32 passed, repeated with no failures |
| `alembic check`, `pip check`, `npm audit`, production build | passed |
| Backup drill on the development database | passed |
| Search p95, 1,000 rows, 200 requests | about 5 ms against a 3,000 ms target |

The search result was measured inside one process on one laptop, with no network. It is not a load test.

Key security and backup checks were also tested by deliberately breaking the code and confirming a test failed.

## Decisions awaiting team approval

PDF-only uploads, required course, downloads only for signed-in users, 60-minute tokens kept in memory, administrators cannot change their own account, deleted materials cannot be recovered except from a backup.

## Not done

- Each student's personal review and contribution statement.
- A run on Windows and Edge. The new tests have not run there.
- Deployment to a real server, a scheduled backup job and backup storage off the server.
- Malware scanning, password reset, email verification and token revocation on logout.
- Load testing, a full accessibility audit and parsing a real 50 MB PDF.
- Translating database content.

## Update 2026-11-13 (Week 11)

Added: request limits (429), TOTP two-factor authentication, search indexes, Kazakh interface, redesigned UI and 20 UX/UI tests. See [WEEK11_TEAM_STATUS.md](WEEK11_TEAM_STATUS.md).
