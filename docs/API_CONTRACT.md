# Shared API contract — implemented Week 10

2026-11-05. This supersedes the planned-only skeleton contract, preserved in history/week10-skeleton/API_CONTRACT.md. All routes below are mounted. PostgreSQL API tests and real browser workflows were executed; see week10/TEST_REPORT.md for exact scope. The earlier skeleton implemented only health.

JSON uses snake_case. Errors: {"error":{"code":"http_<status>","message":"safe text"}}; 422 request validation uses validation_error. Database/storage unavailable => 503. Never return password_hash or file_path. Positive integer resource IDs. No successful fake data responses.

## Public authentication

**POST /api/auth/register** — Talgat/Alibek. JSON required full_name (trimmed 1–120), email (valid, trimmed/lowercase, max 254), password (12–128). Extra fields including role are rejected (422). Success **201**: {"user_id":1,"full_name":"Example Student","email":"student@example.com","role":"student"}. Duplicate normalized email 409; invalid/missing data 422. PostgreSQL unique constraint is authoritative. No token on registration.

**POST /api/auth/login** — JSON email and password (1–128); no extra fields. Success 200: {"access_token":"...","token_type":"bearer"}. Generic invalid credentials 401; invalid body 422; missing valid signing configuration 503. JWT HS256, configured secret, default 60 minutes, required subject/issuer/audience/issued-at/expiry. See conventions for prototype limitations.

**GET /api/auth/me** — Bearer token required. Returns public user object above, including the current database role. Missing/invalid/expired/deleted user => 401. Added to avoid trusting client-decoded roles for navigation; backend still enforces authorization independently.

## Materials and taxonomy

**GET /api/materials** — public. Optional q (0–200 characters, blank means all), category_id/course_id (>0), limit (1–100, default 20), offset (>=0, default 0). Case-insensitive literal substring matching on title, course name or category name; filters combine with search. Newest material_id first. 200:

~~~json
{"items":[{"material_id":1,"uploader_id":1,"category_id":1,"course_id":1,"title":"Programming notes","file_size_bytes":1024,"uploaded_at":"2026-11-05T13:00:00+05:00"}],"total":1,"limit":20,"offset":0}
~~~

No matches => items [], total 0. Invalid query => 422. Three-second performance target under representative load remains unverified.

**POST /api/materials** — authenticated student only. Multipart required title (trimmed 1–200), category_id/course_id (positive existing IDs), file. Required course and PDF-only are Week 10 proposed decisions. File must be 1–52,428,800 actual bytes and a readable, unencrypted PDF with at least one page. Generated filename; uploader_id derives from the current user. Extra client uploader_id/file_path/size values are never trusted. Success 201: one material object shown above. 401 unauthenticated; 403 nonstudent; 413 oversized; 415 unsupported/corrupt/encrypted PDF; 422 invalid references/title or empty file; 503 database/storage failure. Expected application failures clean up .part/final files and roll back metadata; abrupt process crashes remain a documented limitation.

**GET /api/materials/{material_id}/download** — authenticated user (student/admin). 200 actual application/pdf attachment, generated download name, X-Content-Type-Options: nosniff. No JSON body. 401 unauthenticated, 404 missing/unsafe file or material, 422 invalid ID. Public download is not enabled or claimed approved.

**GET /api/categories** — public. 200 {"items":[{"category_id":1,"category_name":"Lecture Notes","description":null,"created_at":"2026-11-05T13:00:00+05:00"}]}. **GET /api/courses** — public. 200 {"items":[{"course_id":1,"course_name":"Introduction to Programming","course_code":"PROG101","description":null}]}. All keys required; descriptions nullable. IDs come from PostgreSQL, never hardcoded in forms. CLI seeds fictional taxonomy, not student accounts.

## Material deletion

**DELETE /api/materials/{material_id}** — the uploader or an admin. 204 with no body; removes the row, then the file. 401 guest, 403 other student, 404 unknown ID.

## Admin and health

All routes under /api/admin require an admin: 401 guest or invalid token, 403 student.

**GET /api/admin/users** — optional q (name or email), limit (1–100, default 50), offset. 200 {"items":[{"user_id":1,"full_name":"Example Student","email":"student@example.com","role":"student","is_active":true}],"total":1,"limit":50,"offset":0}.

**PATCH /api/admin/users/{user_id}** — JSON with role and/or is_active, no other fields. 200 same user object. 404 unknown, 409 changing your own account, 422 invalid or empty body. A blocked user receives 403 on login and on every protected route, immediately.

**GET /api/admin/reports/courses** — 200 {"items":[{"course_id":1,"course_name":"Database Systems","course_code":"DB101","material_count":0}]}, including empty courses, fewest materials first.

**GET /api/admin/reports/downloads** — optional limit (1–100, default 10). 200 {"items":[{"material_id":1,"title":"Notes","course_name":"Programming","download_count":3}],"total_downloads":3}. Only successful downloads are counted.

**GET /api/admin/storage-check** — 200 {"orphan_files":0,"partial_files":0,"missing_files":0}. Counts only, never file names.

**POST /api/admin/categories** — JSON category_name (1–100), optional description. **POST /api/admin/courses** — JSON course_name (1–150), course_code (1–30, stored uppercase), optional description. 201 with the new record, 409 duplicate, 422 invalid.


**GET /api/admin/overview** — authenticated admin only. 200 {"total_users":5,"total_materials":2}, both counts queried from PostgreSQL. 401 guest/invalid token, 403 student. There is no public admin-registration endpoint; local CLI setup is documented in README.

**GET /api/health** — unchanged, public, 200 {"status":"ok","service":"study-materials-backend"}. API availability only, not database readiness. Unknown route 404; unsupported method 405. OpenAPI at /openapi.json and interactive docs at /docs.

## Gamification

**GET /api/gamification/me** — authenticated. XP, level, streak, badges and the last 15 XP events (each with action, signed points, description and material_title when the material still exists).

**GET /api/gamification/leaderboard** — public. limit 1–50 (default 20). Active students with more than 0 XP, highest XP first; administrators are not ranked. No email or other private fields.

**GET /api/gamification/users/{user_id}** — public (a Bearer token is optional; an invalid one is treated as anonymous). Profile of an active student: rank, level and XP, streaks, badges with dates, XP by source, activity per day for the last 84 days, uploaded materials (20 newest) and the last 30 XP events. 404 for admins, blocked or missing users; 422 for an invalid ID. The owner (is_self=true) also sees private details; everyone else does not see the 2FA badge, the 2FA event or the titles of materials the student downloaded.

**XP rules.** Upload +50; downloading another student's material +5 to the student and +10 to the uploader, once per student and material (repeat downloads, own materials and admin downloads earn nothing); enabling 2FA +25 once; AI study session +5 once per day. Moving a material to Trash or deleting it takes its upload XP back (an `upload_revoked` event with negative points); restoring it pays the XP again. Days for streaks and daily limits are local study days (GAMIFICATION_UTC_OFFSET_HOURS, default 5); a streak not continued yesterday is shown as 0. Migration 0006 credits uploads and 2FA made before gamification existed and recomputes XP as the sum of each user's XP events.

## Tested and future scope

Executed PostgreSQL tests cover registration persistence/hash/duplicate/validation, role restrictions, current-role recheck, invalid/expired/forged tokens, real counts, taxonomy, file validation/size/cleanup, FK/PK constraints, search, download and CORS. Browser tests exercise client integration, translation, network errors and the complete workflow. Exact-size counting and simulated DB failure use targeted mocks; no test labeled PostgreSQL substitutes SQLite.

Future endpoints are not implemented: account recovery, email verification, logout/revocation, material editing. No route should return a fake success for these. Formal approval of the prototype decisions remains pending.
