# Module responsibility

Talgat: session.py supplies the shared lazy PostgreSQL engine and request session. seed.py inserts repeatable fictional taxonomy and optional CLI-only admin. Alembic lives in backend/migrations; configuration comes from core/config.py. See docs/week10/TALGAT_BACKEND.md.

Implementation prepared by Codex; personal owner review pending.
