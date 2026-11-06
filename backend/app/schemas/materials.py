from datetime import datetime
from pydantic import BaseModel, ConfigDict

class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: int
    uploader_id: int
    category_id: int
    course_id: int
    title: str
    file_size_bytes: int
    uploaded_at: datetime

class MaterialList(BaseModel):
    items: list[MaterialResponse]
    total: int
    limit: int
    offset: int

class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category_id: int
    category_name: str
    description: str | None
    created_at: datetime

class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    course_id: int
    course_name: str
    course_code: str
    description: str | None

class CategoryList(BaseModel):
    items: list[CategoryResponse]

class CourseList(BaseModel):
    items: list[CourseResponse]
