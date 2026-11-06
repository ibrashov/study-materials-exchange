# Module responsibility

Talgat owns auth.py hashing and signed tokens. Daryn owns storage.py bounded PDF storage, cleanup and safe path resolution. Routes share the same database session and never expose internal paths.

Implementation prepared by Codex; personal owner review pending.
