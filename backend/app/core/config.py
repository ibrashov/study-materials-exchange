from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
MAX_FILE_BYTES = 52_428_800

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / 'backend' / '.env', env_file_encoding='utf-8', extra='ignore')
    cors_origins: list[str] = ['http://localhost:5173', 'http://127.0.0.1:5173']
    database_url: str | None = None
    test_database_url: str | None = None
    auth_secret: str = ''
    token_minutes: int = Field(default=60, ge=1, le=1440)
    uploads_dir: Path = ROOT / 'uploads'
    backups_dir: Path = ROOT / 'backups'
    backup_keep: int = Field(default=7, ge=1, le=365)
    storage_backend: str = 'local'
    supabase_url: str = ''
    supabase_service_role_key: str = ''
    supabase_bucket: str = 'materials'

settings = Settings()
