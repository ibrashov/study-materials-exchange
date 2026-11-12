"""Database and file backups with a manifest, so a restore is checked rather than trusted."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import psycopg
from psycopg import IsolationLevel, sql
from sqlalchemy.engine import make_url
from .pg_tools import pg_tool

TABLES = ('users', 'categories', 'courses', 'materials')
BACKUP_NAME = re.compile(r'^\d{8}-\d{6}-\d{6}$')
RESTORE_SUFFIX = '_restore'

class BackupError(Exception):
    pass

def connect(url, database=None, **options):
    parsed = make_url(url)
    try:
        return psycopg.connect(host=parsed.host, port=parsed.port or 5432, user=parsed.username,
                               password=parsed.password, dbname=database or parsed.database,
                               connect_timeout=5, **options)
    except psycopg.Error:
        raise BackupError(f'Cannot connect to database {database or parsed.database}') from None

def run_tool(name, url, *arguments):
    parsed = make_url(url)
    command = [pg_tool(name), '-h', parsed.host, '-p', str(parsed.port or 5432), '-U', parsed.username, *map(str, arguments)]
    result = subprocess.run(command, env={**os.environ, 'PGPASSWORD': parsed.password or ''}, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'no details'
        raise BackupError(f'{name} failed: {detail}'.replace(parsed.password or '\0', '***'))

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()

def table_counts(connection):
    return {table: connection.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
            for table in TABLES}

def archive_uploads(uploads_dir, target):
    uploads_dir = Path(uploads_dir)
    names = sorted(path.name for path in uploads_dir.glob('*.pdf')) if uploads_dir.is_dir() else []
    archived = []
    with tarfile.open(target, 'w:gz') as archive:
        for name in names:
            try:
                archive.add(uploads_dir / name, arcname=name)
                archived.append(name)
            except FileNotFoundError:
                continue  # Removed while the backup was running.
    return archived

def list_backups(destination):
    destination = Path(destination)
    if not destination.is_dir():
        return []
    return sorted((path for path in destination.iterdir() if path.is_dir() and BACKUP_NAME.match(path.name)),
                  key=lambda path: path.name)

def rotate(destination, keep):
    for path in list_backups(destination)[:-keep]:
        shutil.rmtree(path)

def create_backup(url, uploads_dir, destination, keep=7):
    """Dumps a consistent snapshot and archives files. An incomplete backup is never left behind."""
    from ..core.config import settings
    if settings.storage_backend != 'local':
        raise BackupError('Local backup does not include cloud objects; back up the database and bucket separately')
    if keep < 1:
        raise BackupError('keep must be at least 1')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    working = Path(tempfile.mkdtemp(prefix='.incomplete-', dir=destination))
    try:
        dump, archive = working / 'database.dump', working / 'uploads.tar.gz'
        with connect(url) as connection:
            connection.isolation_level = IsolationLevel.REPEATABLE_READ
            snapshot = connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
            counts = table_counts(connection)
            revision = connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            recorded = {row[0] for row in connection.execute('SELECT file_path FROM materials')}
            run_tool('pg_dump', url, '--format=custom', '--no-owner', '--no-privileges', f'--snapshot={snapshot}',
                     '--file', dump, make_url(url).database)
            files = archive_uploads(uploads_dir, archive)
        manifest = {'format': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'alembic_revision': revision,
                    'tables': counts, 'files': len(files), 'missing_files': sorted(recorded - set(files)),
                    'sha256': {'database.dump': sha256(dump), 'uploads.tar.gz': sha256(archive)}}
        (working / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        final = destination / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        working.rename(final)
    except BaseException:
        shutil.rmtree(working, ignore_errors=True)
        raise
    rotate(destination, keep)
    return final

def verify_backup(path):
    path = Path(path)
    try:
        manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        for name, expected in manifest['sha256'].items():
            if sha256(path / name) != expected:
                raise BackupError(f'{name} does not match its checksum')
    except (OSError, ValueError, KeyError):
        raise BackupError(f'Backup {path.name} is incomplete or unreadable') from None
    return manifest

def restore_backup(path, target_url, uploads_dir, allow_live=False):
    """Replaces the target database in one transaction, restores files, then checks the result."""
    path, uploads_dir = Path(path), Path(uploads_dir)
    manifest = verify_backup(path)
    database = make_url(target_url).database
    if not allow_live and not database.endswith(RESTORE_SUFFIX):
        raise BackupError(f'Refusing to replace {database}; restore into a *{RESTORE_SUFFIX} database or allow it explicitly')
    run_tool('pg_restore', target_url, '--clean', '--if-exists', '--no-owner', '--no-privileges', '--single-transaction',
             '--dbname', database, path / 'database.dump')
    uploads_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path / 'uploads.tar.gz') as archive:
        archive.extractall(uploads_dir, filter='data')
    with connect(target_url) as connection:
        counts = table_counts(connection)
        rows = connection.execute('SELECT file_path, file_size_bytes FROM materials').fetchall()
    if counts != manifest['tables']:
        raise BackupError('Restored row counts do not match the backup')
    checked = 0
    for name, size in rows:
        if name in manifest['missing_files']:
            continue
        restored = uploads_dir / name
        if not restored.is_file() or restored.stat().st_size != size:
            raise BackupError('A restored file is missing or has the wrong size')
        checked += 1
    return {'tables': counts, 'files_checked': checked}

def require_restore_name(url):
    database = make_url(url).database
    if not database.endswith(RESTORE_SUFFIX):
        raise BackupError(f'Refusing to manage {database}; only *{RESTORE_SUFFIX} databases are disposable')
    return database

def drop_restore_database(url):
    database = require_restore_name(url)
    with connect(url, database='postgres', autocommit=True) as connection:
        connection.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(database)))

def prepare_restore_database(url):
    drop_restore_database(url)
    with connect(url, database='postgres', autocommit=True) as connection:
        connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(require_restore_name(url))))

def restore_url_for(url):
    parsed = make_url(url)
    return parsed.set(database=parsed.database + RESTORE_SUFFIX).render_as_string(hide_password=False)

def run_drill(url, uploads_dir, destination, keep=7):
    """Makes a fresh backup and restores it into a throwaway database to prove it works."""
    path = create_backup(url, uploads_dir, destination, keep=keep)
    target = restore_url_for(url)
    with tempfile.TemporaryDirectory() as restored_files:
        prepare_restore_database(target)
        try:
            report = restore_backup(path, target, Path(restored_files))
        finally:
            drop_restore_database(target)
    return {'passed': True, 'backup': path.name, **report}
