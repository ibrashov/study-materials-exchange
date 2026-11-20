from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class BadgeItem(BaseModel):
    code: str
    icon: str
    earned: bool
    earned_at: datetime | None = None


class XpEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    action: str
    points: int
    description: str
    material_title: str | None = None
    created_at: datetime


class GamificationProfile(BaseModel):
    user_id: int
    full_name: str
    xp_points: int
    level: int
    level_code: str
    current_level_xp: int
    next_level_xp: int | None
    progress_percent: int
    current_streak: int
    longest_streak: int
    materials_count: int
    total_downloads_received: int
    badges: list[BadgeItem]
    recent_events: list[XpEventItem]


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    full_name: str
    xp_points: int
    level: int
    level_code: str
    current_streak: int
    materials_count: int
    total_downloads: int
    badges_count: int


class LeaderboardResponse(BaseModel):
    items: list[LeaderboardEntry]


class BadgeCatalogItem(BaseModel):
    code: str
    icon: str
    xp_hint: str


class BadgeCatalogResponse(BaseModel):
    items: list[BadgeCatalogItem]


class XpSource(BaseModel):
    source: str
    xp: int


class ActivityDay(BaseModel):
    date: date
    xp: int
    actions: int


class ProfileUpload(BaseModel):
    material_id: int
    title: str
    download_count: int
    uploaded_at: datetime
    course_code: str
    course_name: str
    category_name: str


class PublicProfile(BaseModel):
    user_id: int
    full_name: str
    is_self: bool
    rank: int | None
    xp_points: int
    level: int
    level_code: str
    current_level_xp: int
    next_level_xp: int | None
    progress_percent: int
    current_streak: int
    longest_streak: int
    last_active_on: date | None
    materials_count: int
    total_downloads_received: int
    students_reached: int
    materials_studied: int
    badges: list[BadgeItem]
    xp_breakdown: list[XpSource]
    activity_days: list[ActivityDay]
    activity_window_days: int
    today: date
    uploads: list[ProfileUpload]
    recent_events: list[XpEventItem]
