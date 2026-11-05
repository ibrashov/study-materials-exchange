# Week 10 verification ? 5 November 2026

Environment: Windows PowerShell, Python 3.14.3, Node 24.13.1, npm 11.8.0, Microsoft Edge through Playwright. Commands are reproducible in root README.

| Check | Actual result |
| --- | --- |
| Original `python -m unittest discover -s tests -v` before edits | 7 tests passed |
| `.venv/Scripts/python -m compileall -q backend tests` | passed |
| Node --check for client, client tests, Playwright config and browser tests | passed |
| `.venv/Scripts/python -m unittest discover -s tests -v` | 10 tests passed (7 original, 3 new) |
| FastAPI/uvicorn startup on 127.0.0.1:8000 | application startup complete; no database configured |
| HTTP health through Node client and real Edge browser | 200 and exact expected status/service |
| New backend tests | health, error envelope, 405, /docs, OpenAPI and allowed/denied CORS passed |
| `npm.cmd test` | 2 tests passed; real HTTP plus HTTP/payload/network failure handling |
| `npm.cmd run build` | passed, Vite 7.3.7, 27 modules transformed |
| `npm.cmd run test:browser` | 2 passed in Edge; real connection/navigation and loading/error/retry |
| `python -m pip --python .venv check` | No broken requirements found |
| `npm.cmd audit` during patched installation | 0 vulnerabilities |
| Historical tracked SQL, ERD, requirements, Week 9 report and database tests | git diff empty; unchanged |
| `git diff --check` | passed (line-ending conversion notices only) |

Initial restricted runs failed because worker spawning was blocked (EPERM), npm was cache-only and venv ensurepip failed. Authorized installation and test execution outside the restricted sandbox succeeded. Host pip installed into .venv using --python; .venv itself has no pip module, so use the documented host pip fallback in this environment. Initial browser failures exposed missing React JSX imports; fixed, rebuilt and both browser checks then passed. Initial Vite dependency audit reported a high-severity vulnerability; upgraded to patched 7.3.7 with zero findings.

Network failure in the browser was deliberately induced by aborting the health request; retry then contacted the actual running backend. This tests frontend error behavior without claiming a production outage test. No PostgreSQL, authentication, storage, search, admin, backup, production deployment or performance tests were executed: those features are not implemented. npm audit is not a Python security audit. No manual student review or manual student testing is claimed.
