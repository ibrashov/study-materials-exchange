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

settings = Settings()
