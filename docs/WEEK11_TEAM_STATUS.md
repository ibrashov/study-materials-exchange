# Week 11 team status — Study Materials Exchange

2026-11-13. Course: Basics of Information Systems. Next milestone: Week 15 working information system. Source of the plan: team table "Plan week 11".

| Student / ID | Plan for week 11 | Delivered | Report |
| --- | --- | --- | --- |
| Kozhakhmetov Talgat 24B031852 | request limit | per-IP sliding-window limits with 429 + Retry-After, per-endpoint rules, settings, tests | [week11/TALGAT_REQUEST_LIMIT.md](week11/TALGAT_REQUEST_LIMIT.md) |
| Ibrashov Anuar 24B031812 | server | shared cloud server (Render + Supabase) was delivered earlier on `main`; see [WEEK11_ANUAR_SERVER.md](WEEK11_ANUAR_SERVER.md) and [DEPLOYMENT.md](DEPLOYMENT.md) | — |
| Ainakul Arnur 24B031609 | 2 authentication / reserve copy | TOTP two-factor authentication (encrypted secrets, Security page); backup/restore tooling already on `main` (BACKUP_RESTORE.md), kept consistent with the new migrations | [week11/ARNUR_2FA_BACKUP.md](week11/ARNUR_2FA_BACKUP.md) |
| Abylay Daryn 24B031598 | database: index, increase the speed | trigram + composite indexes (migration 0002), search query rewrite, benchmark (p95 63.8 → 33.2 ms at 300k rows), benchmark over 300,000 rows (`benchmark_indexes.py`) | [week11/DARYN_INDEXES.md](week11/DARYN_INDEXES.md) |
| Anuarbek Alibek 24B031648 | front design / 20 test ux/ui report | redesigned UI, Kazakh added, translated materials page, 20 automated UX/UI tests + screenshots | [week11/ALIBEK_UX_UI_REPORT.md](week11/ALIBEK_UX_UI_REPORT.md) |

Overall evidence: [week11/TEST_REPORT_WEEK11.md](week11/TEST_REPORT_WEEK11.md) — 87 Python tests, 47 frontend unit tests, 52 browser tests, migrations up/down, all passed on 2026-11-13.

## Personal verification (fill in before presenting)
Every teammate must run their own commands, read their code, and add a dated line below their report: command, output, one change they made themselves. Nothing here claims manual authorship or review by the students.

## Remaining risks for Week 12–15
No recovery codes for lost authenticator; rate-limit state is per process (Render free plan = one process); backups not encrypted or scheduled; Kazakh/Russian texts need native proofreading; accessibility tested automatically only; the Week 10 open items (decision approval, malware scanning, account recovery) remain.
