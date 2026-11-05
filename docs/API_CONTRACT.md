# Shared API contract

Only **GET /api/health is implemented**. Other endpoints below are **Planned ? Proposed ? Team Approval Required**. They are not mounted, return 404 today, and must not be used as successful demos. Health does not inspect storage or PostgreSQL.

All JSON fields use snake_case. JSON bodies use application/json except multipart upload. No public response contains password_hash or an internal file_path. Error shape: `{"error":{"code":"validation_error","message":"Request validation failed"}}`. Status-specific HTTP errors currently use `http_404`, `http_405`, etc. Planned business error codes need team agreement. Positive integer IDs are required. Proposed timestamps use UTC ISO 8601.

## GET /api/health ? implemented and tested

Owner: Anuar. Purpose: API availability. No authentication, body, required or optional parameters. Success 200: `{"status":"ok","service":"study-materials-backend"}`. Response fields are required literal values. Wrong method: 405; unknown route: 404. Infrastructure/network failures are not a successful health response. See VERIFICATION.md for actual checks.

## POST /api/auth/register ? planned

Owner: Talgat backend; Alibek UI. Create student account. Public, JSON. Required: full_name, email, password; no optional fields. Example: `{"full_name":"Example Student","email":"student@example.test","password":"example-only-change-me"}`. Never submit password_hash or role. Trim name, require nonblank name, validate email, reject duplicate normalized email. Proposed password minimum 12 characters; normalization and maximum lengths need agreement. Server assigns student role and hashes password.

Success 201: `{"user_id":1,"full_name":"Example Student","email":"student@example.test","role":"student"}` (all fields required). Errors: 409 duplicate email, 422 missing/invalid input, 500 safe server error. No token is returned by registration in this proposal.

## POST /api/auth/login ? planned

Owner: Talgat backend; Alibek UI. Public JSON, required email and password, no optional fields. Example: `{"email":"student@example.test","password":"example-only-change-me"}`. Validate email/nonempty password; do not log credentials. Success 200: `{"access_token":"<opaque-example>","token_type":"bearer"}`; both required. Errors: 401 generic invalid credentials (avoid account enumeration), 422 invalid body, 500. Token format/lifetime/storage remain proposed; no token service currently exists.

## GET /api/materials ? planned

Owner: Daryn search; Talgat queries; Alibek UI. Public browsing/search (FR-02, BR-01). No body or required query fields. Proposed optional query fields: q (nonblank title/course-name search), category_id and course_id (positive integers), limit (1?100, default 20), offset (>=0, default 0). Example: `/api/materials?q=programming&category_id=1&limit=20&offset=0`. Search uses title or joined course_name; category_id supplies category filtering. Return 200, including empty items when no match:

```json
{"items":[{"material_id":1,"uploader_id":1,"category_id":1,"course_id":1,"title":"Programming notes","file_size_bytes":1024,"uploaded_at":"2026-11-05T08:00:00Z"}],"total":1,"limit":20,"offset":0}
```

All shown response fields required; no optional response fields proposed. Validate IDs, bounds and supported filters. Errors: 422 invalid query, 500 service failure. Three-second search target is not measured by the skeleton.

## POST /api/materials ? planned

Owner: Daryn storage/upload; Talgat metadata/auth; Alibek UI. Authenticated student only. `Authorization: Bearer <token>`. multipart/form-data required fields: title (trimmed nonblank), category_id (positive existing ID), file (actual bytes 1?52,428,800). Proposed required course_id (positive existing ID): schema requires it but requirements still need team approval. No optional fields proposed. Example form: title=Programming notes, category_id=1, course_id=1, file=@notes.pdf. Never accept uploader_id, file_path or file_size_bytes as trusted client metadata.

Success 201: material object from GET /api/materials, all shown fields required. Validate real stream length and references before finalizing; coordinate rollback/cleanup if storage or metadata fails. File type allowlist remains proposed. Errors: 401 unauthenticated, 403 forbidden role, 413 too large, 415 unsupported type after allowlist agreement, 422 invalid fields/references or empty file, 500 storage/database failure. No file or row should remain after a failed operation. Actual storage and cleanup are not implemented.

## GET /api/materials/{material_id}/download ? planned

Owner: Daryn; Talgat metadata access. Purpose: download stored bytes. Proposed public access (requirements allow browsing/search but do not explicitly settle guest download); team must approve access before implementation. Required positive material_id path parameter; no body or optional fields. Success 200 binary stream, safe Content-Disposition attachment filename and correct Content-Type. No JSON success body. Errors: 404 missing metadata/file, 422 invalid ID, 500 storage failure; 401/403 if team chooses restricted downloads. Reject path traversal; resolve stored path server-side.

## GET /api/categories and GET /api/courses ? planned

Owner: Talgat backend; Alibek selectors. Justification: valid upload selectors and search filters need canonical IDs/names. Public, no body/required/optional parameters. Success 200: `{"items":[{"category_id":1,"category_name":"Notes","description":null,"created_at":"2026-11-05T08:00:00Z"}]}` or `{"items":[{"course_id":1,"course_name":"Introduction to Programming","course_code":"PROG101","description":null}]}`. All keys required; nullable description. Empty items allowed. Errors: 500 service failure. No client input validation beyond route/method. These endpoints do not create or modify taxonomy.

Admin operations and separate search endpoints are not specified: requirements do not yet define admin actions, and materials query already covers search. Arnur and Anuar must agree authorization and acceptance criteria before adding admin contracts. All planned validation/security rules need implementation and tests by their owners.
