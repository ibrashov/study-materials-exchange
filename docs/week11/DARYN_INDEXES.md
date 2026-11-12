# Daryn — database indexes and speed (Week 11 plan: "database: index, increase the speed")

Personally verified by Daryn: pending. Files: `backend/migrations/versions/0003_search_indexes.py`, `backend/app/models/entities.py`, `backend/app/api/routes/materials.py`, `scripts/benchmark_indexes.py` (the 1,000-row `benchmark_search.py` already on `main` is unchanged).

## Indexes added (migration 0003, reversible)
| Index | Why |
| --- | --- |
| `ix_materials_title_trgm` (GIN, `pg_trgm`) | `title ILIKE '%text%'` cannot use a normal B-tree; trigram GIN can |
| `ix_courses_name_trgm`, `ix_categories_name_trgm` (GIN) | same for course/category name search (small tables, kept for growth) |
| `ix_materials_course_newest (course_id, material_id DESC)` | filter by course + newest first |
| `ix_materials_category_newest (category_id, material_id DESC)` | filter by category + newest first |

The old single-column `course_id` / `category_id` indexes are dropped: the composite indexes start with the same column, so they cover the same lookups. `uploader_id`, primary keys and unique constraints are unchanged. `alembic check` reports no drift; downgrade → upgrade was run.

## Query change (the part that made the indexes useful)
The old search joined `courses` and `categories` and put three `ILIKE` conditions in one `OR`; PostgreSQL then scanned the whole `materials` table (a 52 ms parallel sequential scan on 300,000 rows for one selective term, vs 2.9 ms when the title condition was alone). Now the endpoint first finds matching course/category ids in those tiny tables and filters `materials` with plain id lists, so PostgreSQL can combine the trigram index and the course/category indexes. Results are identical (search tests PG-search, wildcard escaping `%`, still pass). The count query also drops its unused `ORDER BY`.

## Benchmark (executed 2026-11-13, local PostgreSQL 17.6, 300,000 fixture rows titled `BENCH-n …`)
`scripts/benchmark_indexes.py --rows 300000 --runs 5` drives the real FastAPI endpoint with 9 query shapes (common word, two words, course name, selective prefix, selective id, no match, no filter, category filter, course + text), 45 requests per phase:

| | p50 | p95 |
| --- | --- | --- |
| without Week 11 indexes | 35.1 ms | 63.8 ms |
| with Week 11 indexes | 12.9 ms | 33.2 ms |

Target from the Week 10 notes: search under 3 seconds → **met by a factor of ~90** even without indexes at this size; the indexes mainly pay off as the table grows and for selective searches. At 20,000 rows both variants were ~9 ms (no measurable difference) — that is reported on purpose: small tables do not need indexes. The benchmark uses the test database only, refuses other names, deletes its fixtures and runs locally (HTTP overhead excluded: it uses an in-process client).

The orphan-file report already exists on `main` (`scripts/reconcile_storage.py`).

## Questions you should be able to answer
What does `gin_trgm_ops` do? Why does a leading `%` defeat a B-tree? Why a composite index with `DESC`? What is the cost of an index (writes, disk)? Why did the OR across joined tables ignore the index?
