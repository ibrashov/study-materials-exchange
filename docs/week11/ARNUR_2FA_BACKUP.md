# Arnur — two-factor authentication (Week 11 plan: "2 authentification / reserve copy")

Personally verified by Arnur: pending. Files: `backend/app/services/twofactor.py`, `backend/app/api/routes/auth.py`, `backend/migrations/versions/0004_two_factor.py`, `tests/test_week11.py`, `frontend/src/features/auth/SecurityPage.jsx`.

## 1. Two-factor authentication (TOTP, RFC 6238)
Works with Google Authenticator, Authy, 1Password.

| Endpoint | Purpose |
| --- | --- |
| POST /api/auth/2fa/setup (signed in) | creates a new secret, returns `secret` + `otpauth_uri`; **not active yet** |
| POST /api/auth/2fa/enable `{code}` | activates 2FA after a valid 6-digit code |
| POST /api/auth/2fa/disable `{password, code}` | needs both the password and a current code |
| POST /api/auth/login `{email, password, otp?}` | if 2FA is on and `otp` is missing → 401 `otp_required`; wrong → 401 `otp_invalid` |

- The secret is **encrypted at rest** (Fernet, key derived from `AUTH_SECRET`); the database never holds the plain secret. Changing `AUTH_SECRET` makes stored secrets undecryptable (users would need to re-enrol) — document this before rotating it.
- Codes are accepted with ±1 time-step tolerance (clock drift).
- `REQUIRE_ADMIN_2FA=true` makes admin login return 403 until the admin has enabled 2FA. Default is off so the existing seeded admin is not locked out.
- The password is checked first and the same generic error is used for unknown e-mail / wrong password, so the OTP step does not leak whether an account exists.
- Frontend: new **Security** page (set up, confirm, turn off); the login form shows the code field only after the server asks for it. EN/RU/KK.
- Migration `0004_two_factor` adds `users.totp_secret` and `users.totp_enabled` (downgrade tested).

## 2. Reserve copy (backup / restore)
Already implemented earlier on `main` (`scripts/backup.py`, `backend/app/services/backup.py`, guide in [docs/BACKUP_RESTORE.md](../BACKUP_RESTORE.md), tests in `tests/test_backup.py`). This week's work only keeps it consistent with the new migrations (the backup manifest test now expects revision `0004_two_factor`). Run the drill from BACKUP_RESTORE.md yourself and add your dated output below this report.

## Tests executed
`tests/test_week11.py`: secret encrypted (stored value ≠ secret, decrypts back), enable rejects a wrong code, login needs OTP once enabled (missing / wrong / right), disable needs password + code, 2FA endpoints need authentication, admin policy flag. 
## Limits (say this at the defence)
No recovery codes: if a user loses the authenticator, an administrator must reset `totp_enabled`/`totp_secret` in the database. No QR image (the secret key is shown to type in; the `otpauth_uri` is returned by the API). Backup limits are in BACKUP_RESTORE.md (not encrypted, not scheduled).
