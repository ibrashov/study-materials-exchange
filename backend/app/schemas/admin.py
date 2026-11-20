from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Trimmed = lambda maximum: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=maximum)]

class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    full_name: str
    email: str
    role: Literal['student', 'admin']
    is_active: bool

class AdminUserList(BaseModel):
    items: list[AdminUser]
    total: int
    limit: int
    offset: int

class UserChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['student', 'admin'] | None = None
    is_active: bool | None = None

    @model_validator(mode='after')
    def require_a_change(self):
        if self.role is None and self.is_active is None:
            raise ValueError('Provide role or is_active')
        return self

class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category_name: Trimmed(100)
    description: Trimmed(500) | None = None

class CourseCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    course_name: Trimmed(150)
    course_code: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=30)]
    description: Trimmed(500) | None = None

class CourseReportRow(BaseModel):
    course_id: int
    course_name: str
    course_code: str
    material_count: int

class CourseReport(BaseModel):
    items: list[CourseReportRow]

class DownloadReportRow(BaseModel):
    material_id: int
    title: str
    course_name: str
    download_count: int

class DownloadReport(BaseModel):
    items: list[DownloadReportRow]
    total_downloads: int

class StorageCheck(BaseModel):
    orphan_files: int
    partial_files: int
    missing_files: int

class BackupItem(BaseModel):
    name: str
    created_at: str | None
    alembic_revision: str | None
    tables: dict[str, int]
    files: int
    verified: bool

class BackupScheduleStatus(BaseModel):
    enabled: bool
    interval_hours: int
    hour_utc: int
    keep: int
    storage_backend: str
    supported: bool
    last_run_at: str | None
    next_run_at: str | None
    last_status: str
    last_backup_name: str | None
    last_error: str | None

class BackupListResponse(BaseModel):
    schedule: BackupScheduleStatus
    items: list[BackupItem]

class BackupScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=720)
    hour_utc: int | None = Field(default=None, ge=0, le=23)
    keep: int | None = Field(default=None, ge=1, le=365)

class AgentConfigResponse(BaseModel):
    api_key_configured: bool
    model: str
    max_tokens: int
    temperature: float
    tools_enabled: bool
    max_tool_steps: int
    system_prompt: str
    default_system_prompt: str
    enabled_tools: list[str]
    available_tools: list[str]

class AgentConfigUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: str | None = Field(default=None, min_length=1, max_length=100)
    max_tokens: int | None = Field(default=None, ge=64, le=4000)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    tools_enabled: bool | None = None
    max_tool_steps: int | None = Field(default=None, ge=1, le=8)
    system_prompt: str | None = Field(default=None, max_length=4000)
    enabled_tools: list[str] | None = None
