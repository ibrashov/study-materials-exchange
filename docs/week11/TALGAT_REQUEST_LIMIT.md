# Talgat — request limit (Week 11 plan: "request limit")

Personally verified by Talgat: pending. Files: `backend/app/services/ratelimit.py`, `backend/app/main.py` (middleware), `tests/test_week11.py`.

## What it does
Every `/api/*` request is counted per client IP in a sliding window. When the limit is exceeded the API answers **429** with a `Retry-After` header and the standard error body `{"error": {"code": "http_429", "message": "Too many requests. Try again in N seconds."}}`.

| Rule | Method + path | Limit |
| --- | --- | --- |
| login | POST /api/auth/login | 10 per 60 s |
| register | POST /api/auth/register | 5 per 10 min |
| twofa | POST /api/auth/2fa/* | 10 per 60 s |
| upload | POST /api/materials | 20 per 10 min |
| download | GET /api/materials/{id}/download | 60 per 60 s |
| default | everything else | 120 per 60 s |

The first matching rule wins and each rule has its own counter, so a login flood does not block browsing. The middleware is registered before CORS, so a 429 still carries CORS headers and the browser can read it (`Retry-After` is exposed).

## Settings (`backend/.env`)
- `RATE_LIMIT_ENABLED=true` (default). Set `false` only for load tests; the browser test backend turns it off because it registers many accounts from one IP.
- `TRUST_PROXY_HEADERS=false` (default). Set `true` only behind a reverse proxy you control, otherwise anyone can fake `X-Forwarded-For`.

## Frontend
`errorKey()` maps 429 to a translated message (EN/RU/KK): "Too many attempts. Wait a minute and try again."

## Tests (all executed, see TEST_REPORT_WEEK11.md)
Unit: window slides, clients are independent, rule matching. Integration on PostgreSQL: 10 failed logins then the 11th (even with the right password) gets 429 + Retry-After; 5 registrations then 429; disabled flag; health is not affected by the login rule. Browser: UX13 (429 shown in EN and KK).

## Known limits (be honest in the defence)
State is in process memory: it resets on restart and each worker of a multi-worker server counts separately. For production use a shared store such as Redis. Limits are per IP, so students behind one university NAT share a budget; the numbers above are prototype defaults.

## Questions you should be able to answer
Why per-rule counters? Why is `Retry-After` needed? What happens with two uvicorn workers? Why not trust `X-Forwarded-For` by default?
