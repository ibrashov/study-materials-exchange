from datetime import datetime
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
