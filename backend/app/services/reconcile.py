"""Compares stored files with material rows. A crash can leave the two out of step."""
import time
from sqlalchemy import select
from ..core.config import settings
from ..models.entities import Material

def scan(db):
    directory = settings.uploads_dir.resolve()
    on_disk = {path.name for path in directory.iterdir() if path.is_file()} if directory.is_dir() else set()
    recorded = set(db.scalars(select(Material.file_path)))
    return {'orphan_files': sorted(name for name in on_disk - recorded if name.endswith('.pdf')),
            'partial_files': sorted(name for name in on_disk if name.endswith('.part')),
            'missing_files': sorted(recorded - on_disk)}

def remove_leftovers(db, min_age_seconds=3600):
    """Deletes unreferenced files older than the limit, so running uploads are left alone."""
    found = scan(db)
    directory = settings.uploads_dir.resolve()
    cutoff = time.time() - min_age_seconds
    removed = []
    for name in found['orphan_files'] + found['partial_files']:
        path = directory / name
        if path.stat().st_mtime <= cutoff:
            path.unlink(missing_ok=True)
            removed.append(name)
    return removed
