# Daryn — files, search and database integrity

2026-11-05 · Abylay Daryn · 24B031598.

**Implementation prepared by Codex. Personally verified by Daryn: pending.**

## Result and files

backend/app/services/storage.py implements chunked temporary storage, actual byte counting, PDF header/parser checks, generated names and safe resolved paths. api/routes/materials.py implements taxonomy reads, upload, paginated title/course/category search and authenticated download. schemas/materials.py excludes file_path. models/entities.py and migration 0001_week10 are shared with Talgat, not duplicated. tests/test_week10.py supplies constraint/file tests.

Student-only upload takes title/category_id/course_id/file. User identity comes from the token-backed database dependency. File names supplied by the client are ignored. File bytes go to UPLOADS_DIR; PostgreSQL stores the generated relative name and metadata. The API returns no internal path. A PDF is served only through authenticated attachment download.

## Integrity and cleanup

users.user_id/materials.material_id are unique generated PKs. Every material references existing users/categories/courses. Native integer/check constraints require size 1–52,428,800. Title must be nonblank. PostgreSQL rejected invalid FK values in all three columns and duplicate PKs in executed tests.

save_pdf writes .part, counts actual bytes, validates a readable unencrypted PDF with pages, then renames. The route flushes metadata and validates the response before commit. Application failures roll back and unlink saved bytes. A sudden crash can still orphan a file between rename and commit; reconciliation is not implemented. Structural PDF validation is not malware detection.

## Demonstration and tests

Register/login, upload a small PDF, search its unique title and download it. Run scripts/inspect_database.py to show its material_id/uploader_id/category_id/course_id and size. Inspect the ignored uploads directory locally to show generated filename. Run the PostgreSQL constraint test to demonstrate rejection of an invalid FK without damaging development data.

TEST_REPORT.md PG12–PG19 passed: real bytes saved/downloaded, no-result search, invalid PDFs and references, 50 MB oversize rejection, admin/guest denial, uniqueness/FKs and cleanup. PG15 mocks only the parser to isolate exact maximum counting; PG16 deliberately injects a commit failure. These limitations must be stated honestly.

## Personal review and Week 11

Daryn must personally upload/download a PDF, explain the three FKs, and inspect cleanup. By 2026-11-13: implement a read-only orphan-file reconciliation report, exercise a simulated interruption, and measure title search on 1,000 labeled fixture materials with p95 duration reported against the 3-second target. Guest downloads and additional file formats still require a team decision.
