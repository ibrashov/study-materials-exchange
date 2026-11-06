from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

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
