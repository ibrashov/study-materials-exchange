"""In-app scheduled backup manager with persistent schedule config and runtime status."""
import asyncio
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from ..core.config import settings
from ..db.session import engine_for
from . import backup
from .app_settings import get_json_setting, set_json_setting

log = logging.getLogger(__name__)

SETTING_KEY = 'backup_schedule'


def default_schedule_config() -> dict:
    return {
        'enabled': bool(settings.backup_schedule_enabled),
        'interval_hours': int(settings.backup_interval_hours),
        'hour_utc': int(settings.backup_schedule_hour_utc),
        'keep': int(settings.backup_keep),
    }


def load_schedule_config(db: Session) -> dict:
    raw = get_json_setting(db, SETTING_KEY, default_schedule_config())
    return {
        'enabled': bool(raw.get('enabled', False)),
        'interval_hours': max(1, min(720, int(raw.get('interval_hours', settings.backup_interval_hours)))),
        'hour_utc': max(0, min(23, int(raw.get('hour_utc', settings.backup_schedule_hour_utc)))),
        'keep': max(1, min(365, int(raw.get('keep', settings.backup_keep)))),
    }


def save_schedule_config(db: Session, updates: dict) -> dict:
    current = load_schedule_config(db)
    for key in ('enabled', 'interval_hours', 'hour_utc', 'keep'):
        if key in updates and updates[key] is not None:
            current[key] = updates[key]
    saved = set_json_setting(db, SETTING_KEY, current)
    scheduler.sync_config(saved)
    return saved


def compute_next_run(config: dict, now: datetime | None = None, last_run_at: datetime | None = None) -> datetime | None:
    if not config.get('enabled'):
        return None
    now = now or datetime.now(timezone.utc)
    interval_hours = int(config.get('interval_hours', 24))
    if last_run_at is not None:
        candidate = last_run_at + timedelta(hours=interval_hours)
        if candidate > now:
            return candidate
    if interval_hours == 24:
        hour_utc = int(config.get('hour_utc', 2))
        candidate = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    return now + timedelta(hours=interval_hours)


def list_backup_summaries(destination: Path | None = None) -> list[dict]:
    dest = Path(destination or settings.backups_dir)
    items = []
    for path in reversed(backup.list_backups(dest)):
        try:
            manifest = backup.verify_backup(path)
            items.append({
                'name': path.name,
                'created_at': manifest.get('created_at'),
                'alembic_revision': manifest.get('alembic_revision'),
                'tables': manifest.get('tables', {}),
                'files': int(manifest.get('files', 0)),
                'verified': True,
            })
        except backup.BackupError:
            items.append({
                'name': path.name,
                'created_at': None,
                'alembic_revision': None,
                'tables': {},
                'files': 0,
                'verified': False,
            })
    return items


class BackupScheduler:
    """Lightweight asyncio loop that executes scheduled backups in a worker thread."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._config: dict = default_schedule_config()
        self.last_run_at: datetime | None = None
        self.next_run_at: datetime | None = compute_next_run(self._config)
        self.last_status: str = 'idle'
        self.last_backup_name: str | None = None
        self.last_error: str | None = None

    def reset_state(self) -> None:
        self._config = default_schedule_config()
        self.last_run_at = None
        self.next_run_at = compute_next_run(self._config)
        self.last_status = 'idle'
        self.last_backup_name = None
        self.last_error = None

    def sync_config(self, config: dict) -> None:
        self._config = dict(config)
        self.next_run_at = compute_next_run(self._config, last_run_at=self.last_run_at)

    def status_dict(self, config: dict | None = None) -> dict:
        cfg = config or self._config
        if config is not None:
            self.sync_config(config)
        return {
            'enabled': bool(cfg['enabled']),
            'interval_hours': int(cfg['interval_hours']),
            'hour_utc': int(cfg['hour_utc']),
            'keep': int(cfg['keep']),
            'storage_backend': settings.storage_backend,
            'supported': settings.storage_backend == 'local',
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'last_status': self.last_status,
            'last_backup_name': self.last_backup_name,
            'last_error': self.last_error,
        }

    def run_now(self, db_url: str | None = None, keep: int | None = None) -> dict:
        url = db_url or settings.database_url
        if not url:
            self.last_status = 'error'
            self.last_error = 'DATABASE_URL is not configured'
            raise backup.BackupError(self.last_error)
        keep_count = keep if keep is not None else int(self._config.get('keep', settings.backup_keep))
        try:
            path = backup.create_backup(url, settings.uploads_dir, settings.backups_dir, keep=keep_count)
            manifest = backup.verify_backup(path)
            self.last_run_at = datetime.now(timezone.utc)
            self.last_status = 'ok'
            self.last_backup_name = path.name
            self.last_error = None
            self.next_run_at = compute_next_run(self._config, last_run_at=self.last_run_at)
            return {
                'name': path.name,
                'created_at': manifest.get('created_at'),
                'alembic_revision': manifest.get('alembic_revision'),
                'tables': manifest.get('tables', {}),
                'files': int(manifest.get('files', 0)),
                'verified': True,
            }
        except backup.BackupError as exc:
            self.last_run_at = datetime.now(timezone.utc)
            self.last_status = 'error'
            self.last_error = str(exc)
            self.next_run_at = compute_next_run(self._config, last_run_at=self.last_run_at)
            raise

    def _refresh_from_db(self) -> None:
        if not settings.database_url:
            return
        try:
            engine = engine_for(settings.database_url)
            with Session(engine) as db:
                cfg = load_schedule_config(db)
            self.sync_config(cfg)
        except Exception:
            # Never fail app startup if DB is not yet migrated or unavailable.
            pass

    async def _loop(self) -> None:
        self._refresh_from_db()
        while True:
            try:
                await asyncio.sleep(60)
                if not self._config.get('enabled') or settings.storage_backend != 'local':
                    continue
                now = datetime.now(timezone.utc)
                if self.next_run_at and now >= self.next_run_at:
                    log.info('Running scheduled backup...')
                    await asyncio.to_thread(self.run_now)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.warning('Scheduled backup run failed: %s', exc)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None


scheduler = BackupScheduler()
