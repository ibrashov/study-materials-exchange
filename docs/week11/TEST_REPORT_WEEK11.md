# Week 11 executed test report

Date: 2026-11-13. Environment: macOS, Python 3.15.2, Node 26.0, PostgreSQL 17, Chrome via Playwright (project-local instance on port 55432), Chromium via Playwright 1.64.1. Separate `study_materials_test` database; development database untouched by tests.

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `.venv/bin/python -m unittest discover -s tests -v` | **87 passed** (76 already on `main` + 11 Week 11: 2 rate-limit unit, 3 limits, 4 two-factor, 2 search/index) |
| Migrations | `alembic downgrade 0002_admin_reports`, `upgrade head`, `alembic check` | up/down work; no drift |
| Frontend unit | `cd frontend && node --test tests/*.test.js` | 47 passed |
| Browser (all) | `cd frontend && npx playwright test` | **52 passed** (32 on `main` + 20 UX/UI) |
| Build | `npm run build` | passed |
| Search benchmark | `scripts/benchmark_indexes.py --rows 300000 --runs 5` | p95 63.8 → 33.2 ms; see DARYN_INDEXES.md |

## Week 11 Python tests (tests/test_week11.py, test_backup.py)
tests/test_week11.py — rate-limit unit: sliding window + retry-after + independent clients; rule matching. PostgreSQL: login 429 + Retry-After; register 429 on the 6th; limiter can be disabled; health not blocked; 2FA secret encrypted and enable needs valid code; login OTP missing/wrong/right; disable needs password + code; 2FA needs authentication; admin 2FA policy; search matches title/course/category and escapes `%`; expected indexes exist.

## Things that went wrong and were fixed (not hidden)
- Adding rate limits first broke tests that log in/register more often than the limits allow (they register/login more often than the limits allow); fixed by resetting the limiter in `setUp`, and the limits are tested separately.
- The public user object now contains `totp_enabled`; the Week 10 test that pinned the exact field set was updated on purpose.
- First benchmark showed **no** gain from the new indexes: the OR/IN-subquery form of the search prevented index use. The query was rewritten (see DARYN_INDEXES.md) and re-measured.

## Not run / not claimed
No Windows run, no Edge run, no second-machine run, no load test beyond the single-client benchmark, no security audit, no Docker/HTTPS/cloud deployment.
