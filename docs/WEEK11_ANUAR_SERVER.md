# Week 11 — server and integration

Previously each installation used its own PostgreSQL and local PDF files. This change prepares Render deployment, shared PostgreSQL configuration and a private Supabase Storage option while preserving the existing local option, authentication and UI. FastAPI stores generated object names in the existing material rows and serves downloads only through the authenticated endpoint. The frontend receives its API URL at build time; FastAPI receives database and storage secrets as server environment variables. Existing database, authentication, file-management and frontend features remain the work of their respective teammates.

Deployed frontend: https://study-materials-web.onrender.com/  
Backend: https://study-materials-api-v15q.onrender.com/api/health

On 12 November 2026, 76 backend tests passed against a separate local PostgreSQL test instance, and 44 frontend tests passed with a local API. Against the deployed service, independent HTTP clients registered and logged in as a test student, confirmed invalid login, guest upload/download denial and student admin denial, uploaded and searched for a PDF, and downloaded identical bytes. The object appeared in the private bucket. After a Render service restart, the same account logged in and downloaded identical bytes again. The test material was deleted and the bucket was confirmed empty. Several synthetic test accounts remain in the database. Two physical devices have not been tested; use `SECOND_DEVICE_TEST.md` for that demonstration.

Cloud backup and restoration have not been tested. Local storage backup/reconciliation does not cover cloud files. The legacy Supabase service-role key is used by the current integration; Supabase states that legacy keys will be retired in early 2027, so migrate the integration before then. Free plans have usage and availability limits. The pull request remains a draft pending team review.
