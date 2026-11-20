"""Gamification service: XP points, streaks, levels, badges, and leaderboard."""
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..models.entities import Material, User, UserBadge, XpEvent

XP_REWARDS = {
    'upload_material': 50,
    'download_material': 5,
    'received_download': 10,
    'enable_2fa': 25,
    'ai_study_session': 5,
}

LEVELS = (
    (1, 'novice', 0),
    (2, 'contributor', 50),
    (3, 'scholar', 150),
    (4, 'mentor', 350),
    (5, 'legend', 700),
)

BADGE_CATALOG = (
    {'code': 'first_upload', 'icon': '📄', 'xp_hint': '1+ upload'},
    {'code': 'prolific_author', 'icon': '📚', 'xp_hint': '5+ uploads'},
    {'code': 'popular_notes', 'icon': '🔥', 'xp_hint': '10+ downloads received'},
    {'code': 'curious_learner', 'icon': '🎓', 'xp_hint': '3+ downloads'},
    {'code': 'security_champion', 'icon': '🛡️', 'xp_hint': '2FA enabled'},
    {'code': 'streak_starter', 'icon': '⚡', 'xp_hint': '3-day streak'},
    {'code': 'rising_star', 'icon': '⭐', 'xp_hint': '150+ XP'},
)


def compute_level(xp_points: int) -> dict:
    xp = max(0, int(xp_points or 0))
    current = LEVELS[0]
    next_threshold: int | None = None
    for idx, entry in enumerate(LEVELS):
        if xp >= entry[2]:
            current = entry
            next_threshold = LEVELS[idx + 1][2] if idx + 1 < len(LEVELS) else None
    if next_threshold is None:
        progress_percent = 100
    else:
        span = max(1, next_threshold - current[2])
        progress_percent = min(100, int(((xp - current[2]) / span) * 100))
    return {
        'level': current[0],
        'level_code': current[1],
        'current_level_xp': current[2],
        'next_level_xp': next_threshold,
        'progress_percent': progress_percent,
    }


def _update_streak(user: User, today: date) -> None:
    if user.last_activity_date == today:
        return
    if user.last_activity_date == today - timedelta(days=1):
        user.current_streak = (user.current_streak or 0) + 1
    else:
        user.current_streak = 1
    user.longest_streak = max(user.longest_streak or 0, user.current_streak)
    user.last_activity_date = today


def evaluate_badges(db: Session, user: User) -> list[str]:
    """Check and award any newly earned badges for user without committing."""
    existing = set(db.scalars(select(UserBadge.badge_code).where(UserBadge.user_id == user.user_id)).all())

    active_uploads = db.scalar(
        select(func.count()).select_from(Material)
        .where(Material.uploader_id == user.user_id, Material.deleted_at.is_(None))
    ) or 0
    downloads_received = db.scalar(
        select(func.coalesce(func.sum(Material.download_count), 0))
        .where(Material.uploader_id == user.user_id, Material.deleted_at.is_(None))
    ) or 0
    downloads_made = db.scalar(
        select(func.count()).select_from(XpEvent)
        .where(XpEvent.user_id == user.user_id, XpEvent.action == 'download_material')
    ) or 0

    earned_now: list[str] = []
    checks = {
        'first_upload': active_uploads >= 1,
        'prolific_author': active_uploads >= 5,
        'popular_notes': downloads_received >= 10,
        'curious_learner': downloads_made >= 3,
        'security_champion': bool(user.totp_enabled),
        'streak_starter': (user.longest_streak or 0) >= 3,
        'rising_star': (user.xp_points or 0) >= 150,
    }
    for code, satisfied in checks.items():
        if satisfied and code not in existing:
            db.add(UserBadge(user_id=user.user_id, badge_code=code))
            earned_now.append(code)
    return earned_now


def award_xp(
    db: Session,
    user: User,
    action: str,
    description: str,
    *,
    points: int | None = None,
    once_ever: bool = False,
    once_per_day: bool = False,
) -> int:
    """Award XP, update streak, record XpEvent, and evaluate badges. Caller commits."""
    amount = XP_REWARDS.get(action, 0) if points is None else points
    if amount <= 0:
        return 0
    today = datetime.now(timezone.utc).date()

    if once_ever:
        already = db.scalar(
            select(XpEvent.event_id)
            .where(XpEvent.user_id == user.user_id, XpEvent.action == action)
            .limit(1)
        )
        if already is not None:
            evaluate_badges(db, user)
            return 0

    if once_per_day:
        start_of_day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        already_today = db.scalar(
            select(XpEvent.event_id)
            .where(
                XpEvent.user_id == user.user_id,
                XpEvent.action == action,
                XpEvent.created_at >= start_of_day,
            )
            .limit(1)
        )
        if already_today is not None:
            return 0

    user.xp_points = (user.xp_points or 0) + amount
    _update_streak(user, today)
    db.add(XpEvent(user_id=user.user_id, action=action, points=amount, description=description[:200]))
    db.flush()
    evaluate_badges(db, user)
    return amount


def get_user_profile(db: Session, user: User) -> dict:
    # Ensure badges are up to date (e.g., if user already had uploads/2FA before gamification existed).
    newly_earned = evaluate_badges(db, user)
    if newly_earned:
        db.commit()

    earned_rows = db.scalars(
        select(UserBadge).where(UserBadge.user_id == user.user_id).order_by(UserBadge.earned_at)
    ).all()
    earned_map = {row.badge_code: row.earned_at for row in earned_rows}

    materials_count = db.scalar(
        select(func.count()).select_from(Material)
        .where(Material.uploader_id == user.user_id, Material.deleted_at.is_(None))
    ) or 0
    total_downloads_received = db.scalar(
        select(func.coalesce(func.sum(Material.download_count), 0))
        .where(Material.uploader_id == user.user_id, Material.deleted_at.is_(None))
    ) or 0
    recent_events = db.scalars(
        select(XpEvent)
        .where(XpEvent.user_id == user.user_id)
        .order_by(XpEvent.event_id.desc())
        .limit(15)
    ).all()

    level_info = compute_level(user.xp_points)
    return {
        'user_id': user.user_id,
        'full_name': user.full_name,
        'xp_points': user.xp_points or 0,
        **level_info,
        'current_streak': user.current_streak or 0,
        'longest_streak': user.longest_streak or 0,
        'materials_count': materials_count,
        'total_downloads_received': total_downloads_received,
        'badges': [
            {
                'code': item['code'],
                'icon': item['icon'],
                'earned': item['code'] in earned_map,
                'earned_at': earned_map.get(item['code']),
            }
            for item in BADGE_CATALOG
        ],
        'recent_events': recent_events,
    }


def get_leaderboard(db: Session, limit: int = 20) -> list[dict]:
    mat_sub = (
        select(
            Material.uploader_id.label('uid'),
            func.count(Material.material_id).label('materials_count'),
            func.coalesce(func.sum(Material.download_count), 0).label('total_downloads'),
        )
        .where(Material.deleted_at.is_(None))
        .group_by(Material.uploader_id)
        .subquery()
    )
    badge_sub = (
        select(
            UserBadge.user_id.label('uid'),
            func.count(UserBadge.badge_id).label('badges_count'),
        )
        .group_by(UserBadge.user_id)
        .subquery()
    )

    rows = db.execute(
        select(
            User.user_id,
            User.full_name,
            User.xp_points,
            User.current_streak,
            func.coalesce(mat_sub.c.materials_count, 0).label('materials_count'),
            func.coalesce(mat_sub.c.total_downloads, 0).label('total_downloads'),
            func.coalesce(badge_sub.c.badges_count, 0).label('badges_count'),
        )
        .outerjoin(mat_sub, mat_sub.c.uid == User.user_id)
        .outerjoin(badge_sub, badge_sub.c.uid == User.user_id)
        .where(User.is_active.is_(True))
        .order_by(User.xp_points.desc(), func.coalesce(mat_sub.c.materials_count, 0).desc(), User.user_id.asc())
        .limit(limit)
    ).all()

    result = []
    for rank, row in enumerate(rows, start=1):
        level_info = compute_level(row.xp_points)
        result.append({
            'rank': rank,
            'user_id': row.user_id,
            'full_name': row.full_name,
            'xp_points': row.xp_points or 0,
            'level': level_info['level'],
            'level_code': level_info['level_code'],
            'current_streak': row.current_streak or 0,
            'materials_count': int(row.materials_count or 0),
            'total_downloads': int(row.total_downloads or 0),
            'badges_count': int(row.badges_count or 0),
        })
    return result
