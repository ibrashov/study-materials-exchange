# Arnur — admin and validation testing

2026-11-05 · Ainakul Arnur · 24B031609.

**Implementation prepared by Codex. Personally verified by Arnur: pending.**

## Result and files

backend/app/api/dependencies.py validates bearer identity, loads the current PostgreSQL user and enforces student/admin roles. api/routes/admin.py counts User and Material rows. frontend/src/features/admin/AdminPage.jsx displays loading, failure, denied and real-count states. Public registration cannot create admins. backend/app/db/seed.py --admin is a local-only prompt/env-based setup command; it refuses to promote existing students and does not commit passwords.

## Validation matrix

Command: .venv/Scripts/python.exe -m unittest discover -s tests -v. Exact methods and additional cases are in TEST_REPORT.md.

| ID | Scenario | Expected | Actual | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| A01 | Valid registration | 201 with saved row | 201 and persisted Argon2 row | Pass | PG01 |
| A02 | Missing fields | 422 | 422 | Pass | PG02 |
| A03 | Duplicate email | 409 | 409 after normalization | Pass | PG03 |
| A04 | Invalid email | 422 | 422 | Pass | PG04 |
| A05 | Student admin request | 403 | 403 | Pass | PG06 |
| A06 | Admin request | 200 real counts | 200, fixture counts match | Pass | PG07 |
| A07 | Guest request | 401 | 401 | Pass | PG08 |
| A08 | Invalid/expired/forged token | 401 | 401 | Pass | PG09 |
| A09 | Inject admin role at registration | 422 | 422 | Pass | PG05 |
| A10 | Role changed after token issue | database role enforced | old admin denied | Pass | PG11 |
| A11 | Admin browser page | actual statistics visible | visible | Pass | Edge admin scenario |
| A12 | Personal demonstration | Arnur repeats checks | not yet recorded | Not Run | student review pending |

## Demonstration

Run the admin seed command from README with a separate local email/password. In /docs, login as a student, copy access_token to Authorize and GET /api/admin/overview: 403. Authorize with an admin token: 200. Open Admin in the signed-in browser to show counts. Never use a frontend role toggle to grant access.

Likely explanation: a bearer token identifies a user; PostgreSQL stores the current role. Hiding the Admin button improves navigation but the backend dependency is what denies students.

## Personal review and Week 11

Arnur must rerun the six required cases, inspect current_user/require_admin and capture his own output. By 2026-11-13: add at least five permission/validation regression cases, including encrypted PDFs and missing stored files, and produce a personally executed test matrix. Broad accessibility and production security reviews remain unfinished.
