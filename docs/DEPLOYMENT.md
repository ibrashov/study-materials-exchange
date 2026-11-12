# Week 11 deployment (pending verification)

The proposed setup is a Render Free web service and static site, Supabase PostgreSQL and a private Storage bucket named `materials`. Do not enable public access to the bucket or expose the service-role key in Vite. The supplied `render.yaml` describes the two Render services. Provisioning has not yet been verified end to end.

1. In Supabase create a private bucket `materials` allowing `application/pdf` and ensure the global upload limit supports the application's 50 MiB limit. Set a lower limit if necessary, consistently with application validation.
2. Obtain the session-pooler PostgreSQL URL (IPv4) with TLS and change its scheme to `postgresql+psycopg://`; URL-encode password characters. Configure it as `DATABASE_URL` in Render only. Keep test databases separate. Never put secrets in Git.
3. Create the services from the feature branch. Supply `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` and `CORS_ORIGINS` (JSON array containing the exact HTTPS frontend origin) to the backend. Supply `VITE_API_BASE_URL` as the backend HTTPS URL ending in `/api` to the static site. Render generates `AUTH_SECRET` for the backend.
4. Startup applies Alembic migrations and adds the existing idempotent taxonomy seed before starting FastAPI. Review migrations and back up existing data before applying them to any populated database. Do not run destructive test suites against cloud production.
5. Verify `/api/health`, registration, login from a separate browser, PDF upload/download, access control, and persistence after a backend restart. The health endpoint checks the API process, not database or storage readiness.

The existing backup and reconciliation tools cover local files only; they refuse to claim coverage of Supabase Storage. Back up PostgreSQL separately using a compatible `pg_dump`, and export the bucket objects separately using Supabase's supported Storage or S3 API. Secure and test restoration in an isolated environment. Database and object backups taken at different times are not automatically consistent. A failed object deletion can leave an orphan and must be investigated in the bucket; a network timeout can also leave an object whose upload outcome is uncertain.

Render Free sleeps after inactivity and can take about a minute to wake. Its filesystem is ephemeral; uploads must use the private cloud bucket. Usage limits and billing terms should be checked before deployment. See https://render.com/docs/free and https://supabase.com/docs/guides/storage/uploads/file-limits.
