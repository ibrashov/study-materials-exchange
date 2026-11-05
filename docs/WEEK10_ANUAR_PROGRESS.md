# Week 10 ? Ibrashov Anuar

Role: Project Manager & System Analyst. Course: Basics of Information Systems.

## Integration problem and contribution

Five developers need a common structure before independently building features. Otherwise names, payloads, endpoints and configuration can diverge. This contribution supplies a runnable shared foundation plus explicit ownership and contracts. It preserves the Week 9 SQLite prototype and does not claim PostgreSQL or other members' features are complete.

Implemented: FastAPI entry point and central router, typed health response, restricted local CORS, environment settings, safe shared HTTP/validation error envelopes and /docs. React/Vite provides project navigation, planned module pages and a shared API client. Backend status is obtained through real HTTP with loading, timeout, error and retry states. The database configuration is reserved for Talgat; no connection is opened.

The [complete file manifest](WEEK10_FILE_MANIFEST.md) lists every created/modified file. Main contributions are frontend/, backend/, TEAM_CONVENTIONS.md, API_CONTRACT.md, ARCHITECTURE.md, root README, backend/client/browser tests and verification evidence. Existing database scripts, ERD, requirements and seven original tests were not edited.

## Verification and shared standards

[Verification evidence](VERIFICATION.md): seven original tests passed before changes; all ten Python tests passed afterward. Two client tests and two real Edge browser tests passed, including real frontend-to-backend communication and a controlled network failure followed by retry recovery. Production build and dependency consistency passed. npm audit reported zero vulnerabilities after patching Vite. The assistant executed these checks; no claim is made that Anuar personally ran them.

Conventions cover canonical schema columns, snake_case JSON, API URLs/methods, public versus internal fields, errors, environment variables, ownership, branches, commits, PR reviews and testing. Existing constraints remain: student/admin roles, guest browse/search, authenticated student uploads, and 1?52,428,800 bytes. Proposed decisions are marked for approval, including course selection, pagination, bearer tokens and guest downloads.

## How the team uses this

Talgat adds PostgreSQL/auth services without changing historical SQLite work. Daryn builds storage/search/download against agreed contracts. Alibek adds forms, materials pages and locales through the central client. Arnur adds admin and authorization/integration tests. Anuar coordinates shared router/config/contract edits and tracks dependencies.

## Limitations and next measurable task

No actual authentication, PostgreSQL schema/connection, stored files, material records, search, downloads, administration or multilingual behavior exists. Health is not database readiness. Production security, backup/restore and performance need future work. Course selection conflicts with the still-proposed requirement extension; agree it before upload implementation. Token policy and admin acceptance criteria also need team agreement.

Week 11 target for Anuar: record team decisions on course selection and auth payloads, review one PR from each affected owner, and coordinate a tested registration ? login ? one valid upload demonstration plus guest-denial/oversize negative cases. This is planned work, not a completed contribution.

## AI assistance disclosure

The scaffold, documentation and tests were generated/edited with AI assistance, and the assistant executed the recorded checks. Anuar's personal review, edits, manual tests, team approval and GitHub commit are pending and must be recorded truthfully after he performs them. This report does not attribute AI-generated code or assistant-run tests to manual student work.

## Seven-minute presentation outline (simple English)

1. **0:00?1:00 ? Problem:** ?Our five developers need one shared structure so that our features can connect without different field names or API paths.?
2. **1:00?2:00 ? Architecture:** ?React calls FastAPI through one API client. PostgreSQL and file storage are planned integrations. Our Week 9 SQLite work is preserved.?
3. **2:00?3:30 ? Demo:** Open Home, show the real backend status and /docs. Stop FastAPI, click Check connection and show the error. Restart it and retry. Open a planned module and explain ownership.
4. **3:30?5:00 ? Standards:** Show TEAM_CONVENTIONS.md and API_CONTRACT.md. Explain snake_case, private password_hash, upload limit and authenticated uploads. Point out team decisions that still need approval.
5. **5:00?6:00 ? Evidence:** Show 10 Python tests, 2 API-client tests, 2 browser tests and the successful production build. Explain AI assistance and which checks you later repeat yourself.
6. **6:00?7:00 ? Next step:** ?My contribution is the integration foundation and common standards. The other developers keep ownership of their features. Next we agree the open decisions and integrate one real user workflow.?

Suggested manual commit message: `chore(architecture): add shared full-stack skeleton and team conventions`. No commit or push was performed by the assistant.
