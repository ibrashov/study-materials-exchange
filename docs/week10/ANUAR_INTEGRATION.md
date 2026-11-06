# Anuar — integration and coordination

2026-11-05 · Ibrashov Anuar · 24B031812.

**Implementation prepared by Codex. Personally verified by Anuar: pending.** Existing skeleton contributions remain separately documented in WEEK10_ANUAR_PROGRESS.md; no claim is made that Anuar manually reviewed or fixed this generated extension.

## Original problem and existing foundation

The previous commits provided React/Vite, FastAPI health, a central client/router, configuration, shared error format, contracts and SQLite evidence. Feature modules could not yet exchange persistent users/materials. Recreating that foundation would lose the agreed interfaces.

## New integration work

Kept /api routes, snake_case JSON and canonical database fields. Connected feature routers once, enabled POST/Authorization CORS for explicit local origins, added safe database/storage errors, extended the shared client and introduced auth/me for current identity. One SQLAlchemy session/model set supports all modules. Frontend selectors load real taxonomy. Course is required to match the schema; downloads remain authenticated; PDF-only and token choices are explicitly proposed Week 10 decisions.

~~~mermaid
sequenceDiagram
    participant UI as Registration UI
    participant Client as Shared client
    participant API as FastAPI
    participant DB as PostgreSQL
    UI->>Client: validated name/email/password
    Client->>API: POST /api/auth/register
    API->>API: normalize + validate + Argon2 hash
    API->>DB: INSERT users then COMMIT
    DB-->>API: persisted user_id
    API-->>Client: 201 public user
    Client-->>UI: show successful registration
~~~

## Evidence and problems resolved

29 Python tests passed, including real PostgreSQL persistence and CORS/contract checks; 2 client tests and 7 Edge browser tests passed; build, migration drift and dependency checks passed. Browser test runs the full registration/login/upload/search/download path through HTTP and a separate PostgreSQL database. See TEST_REPORT.md for individual cases and mock scope.

Problems: existing PostgreSQL service required unknown credentials; an isolated authenticated project cluster on 55432 solved setup without changing that service. Sandbox denied Node processes/temp files; approved execution resolved the environmental issue. Windows browser launcher needed quoting. Browser tests found select-label targeting, inherited test-password setup, and hover contrast issues; they were corrected without changing permissions. No Git merge conflicts existed (initial working tree was clean).

## Documents and ownership

Updated README, TEAM_CONVENTIONS, API_CONTRACT and ARCHITECTURE; preserved originals under docs/history/week10-skeleton. Prepared five role reports, professor-facing team status, seven-minute demo, test report and commit groups. Module ownership describes review responsibility; generated implementation is never falsely attributed to teammates.

## Risks and Week 11 task

Team approval and personal reviews remain pending. Search target under representative load, backup/restore, crash-orphan reconciliation, rate limiting, malware scanning and production hardening remain unverified/unimplemented. Browser tokens are memory-only but remain usable until expiry if copied. No public guest download is enabled.

By 2026-11-13: collect five dated personal reviews, record the four outstanding course/file/download/token decisions, and run the documented browser-to-database demo on a second Windows machine. Expected evidence: five review entries, decision log, reproducible setup log and a passing workflow report. Anuar's task is integration coordination, not claiming Talgat's database or Alibek's UI implementation as personal work.
