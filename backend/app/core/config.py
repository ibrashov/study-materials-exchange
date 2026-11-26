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
    backup_schedule_enabled: bool = False
    backup_interval_hours: int = Field(default=24, ge=1, le=720)
    backup_schedule_hour_utc: int = Field(default=2, ge=0, le=23)
    # Week 11: request limits and two-factor policy
    rate_limit_enabled: bool = True
    trust_proxy_headers: bool = False
    require_admin_2fa: bool = False
    storage_backend: str = 'local'
    supabase_url: str = ''
    supabase_service_role_key: str = ''
    supabase_bucket: str = 'materials'
    # Week 12: ML filename moderation artifact path
    moderation_model_path: Path = ROOT / 'ml_moderation' / 'models' / 'filename_moderator.joblib'
    # Study assistant chatbot (optional): Google Gemini
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-3.6-flash'
    gemini_fallback_model: str = 'gemini-3.1-flash-lite'
    chatbot_max_tokens: int = Field(default=800, ge=64, le=4000)
    chatbot_temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    # Read-only database tools for the assistant (services/chat_tools.py)
    chatbot_tools_enabled: bool = True
    # Gamification: streaks and daily limits follow the local study day (Kazakhstan is UTC+5 all year)
    gamification_utc_offset_hours: int = Field(default=5, ge=-12, le=14)

settings = Settings()
