"""Gamification service: XP points, streaks, levels, badges, and leaderboard.

Rules that keep the score honest:
- Download XP is paid once per (student, material). Repeat downloads, downloads of your own
  material and downloads by administrators earn nothing for anyone.
- Upload XP belongs to a live material: moving it to Trash (or deleting it) takes the XP back,
  restoring it pays it again. Uploading, deleting and re-uploading therefore cannot farm XP.
- Every award locks the user's row, so parallel requests cannot lose XP updates, and badges are
  inserted with ON CONFLICT DO NOTHING, so parallel badge checks cannot fail with a 500.
- "Today" for streaks and daily limits is the local study day (UTC+5 by default, Kazakhstan),
  not the UTC day that would roll over at 05:00 in Almaty.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.entities import Category, Course, Material, User, UserBadge, XpEvent

XP_REWARDS = {
    'upload_material': 50,
    'download_material': 5,
    'received_download': 10,
    'enable_2fa': 25,
    'ai_study_session': 5,
}
# Negative event written when an uploaded material leaves the catalogue (Trash or deletion).
UPLOAD_REVOKED = 'upload_revoked'

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


def local_timezone() -> timezone:
    return timezone(timedelta(hours=settings.gamification_utc_offset_hours))


def local_today(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(local_timezone()).date()


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


def effective_streak(current_streak: int | None, last_activity_date: date | None, today: date | None = None) -> int:
    """The stored streak is only updated on activity; after a missed day it is really 0."""
    today = today or local_today()
    if last_activity_date is None or last_activity_date < today - timedelta(days=1):
        return 0
    return current_streak or 0


def _lock_users(db: Session, *users: User) -> None:
    """Write pending changes, then lock and reload the user rows (in id order, to avoid deadlocks)."""
    db.flush()
    for user in sorted({u.user_id: u for u in users if u is not None}.values(), key=lambda u: u.user_id):
        db.refresh(user, with_for_update=True)


def _has_event(db: Session, user_id: int, action: str, material_id: int | None = None) -> bool:
    query = select(XpEvent.event_id).where(XpEvent.user_id == user_id, XpEvent.action == action)
    if material_id is not None:
        query = query.where(XpEvent.material_id == material_id)
    return db.scalar(query.limit(1)) is not None


def evaluate_badges(db: Session, user: User) -> list[str]:
    """Award any newly earned badges for user without committing. Safe to run in parallel."""
    existing = set(db.scalars(select(UserBadge.badge_code).where(UserBadge.user_id == user.user_id)).all())

    active_uploads = db.scalar(
        select(func.count()).select_from(Material)
        .where(Material.uploader_id == user.user_id, Material.deleted_at.is_(None))
    ) or 0
    # One event per (student, material) pair, so self-downloads and repeat downloads do not count.
    downloads_received = db.scalar(
        select(func.count()).select_from(XpEvent)
        .where(XpEvent.user_id == user.user_id, XpEvent.action == 'received_download')
    ) or 0
    downloads_made = db.scalar(
        select(func.count()).select_from(XpEvent)
        .where(XpEvent.user_id == user.user_id, XpEvent.action == 'download_material')
    ) or 0

    checks = {
        'first_upload': active_uploads >= 1,
        'prolific_author': active_uploads >= 5,
        'popular_notes': downloads_received >= 10,
        'curious_learner': downloads_made >= 3,
        'security_champion': bool(user.totp_enabled),
        'streak_starter': (user.longest_streak or 0) >= 3,
        'rising_star': (user.xp_points or 0) >= 150,
    }
    earned_now: list[str] = []
    for code, satisfied in checks.items():
        if not satisfied or code in existing:
            continue
        inserted = db.execute(
            pg_insert(UserBadge)
            .values(user_id=user.user_id, badge_code=code)
            .on_conflict_do_nothing(constraint='uq_user_badges_user_code')
            .returning(UserBadge.badge_id)
        ).scalar()
        if inserted is not None:
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
    material_id: int | None = None,
) -> int:
    """Add an XP event (positive or negative), update streak and badges. Caller commits.

    Returns the points actually applied (0 when nothing was awarded).
    """
    amount = XP_REWARDS.get(action, 0) if points is None else points
    if amount == 0:
        return 0
    _lock_users(db, user)

    if once_ever and _has_event(db, user.user_id, action):
        evaluate_badges(db, user)
        return 0

    today = local_today()
    if once_per_day:
        start_of_day = datetime(today.year, today.month, today.day, tzinfo=local_timezone())
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

    user.xp_points = max(0, (user.xp_points or 0) + amount)
    if amount > 0:
        _update_streak(user, today)
    db.add(XpEvent(user_id=user.user_id, action=action, points=amount, description=description[:200],
                   material_id=material_id))
    db.flush()
    evaluate_badges(db, user)
    return amount


def reward_download(db: Session, downloader: User, material: Material) -> int:
    """Pay download XP once per (student, material) to the downloader and to the uploader."""
    if downloader.role != 'student' or material.uploader_id == downloader.user_id:
        return 0
    uploader = db.get(User, material.uploader_id)
    # Lock both rows first so two parallel first downloads cannot both pass the check below.
    _lock_users(db, downloader, uploader)
    if _has_event(db, downloader.user_id, 'download_material', material.material_id):
        return 0
    earned = award_xp(db, downloader, 'download_material', f'Downloaded "{material.title}"',
                      material_id=material.material_id)
    if uploader is not None and uploader.is_active:
        award_xp(db, uploader, 'received_download', f'Download received on "{material.title}"',
                 material_id=material.material_id)
    return earned


def _upload_balance(db: Session, user_id: int, material_id: int) -> tuple[int, bool]:
    """Net upload XP currently held for a material and whether it was ever revoked."""
    rows = db.execute(
        select(XpEvent.action, XpEvent.points)
        .where(
            XpEvent.user_id == user_id,
            XpEvent.material_id == material_id,
            XpEvent.action.in_(('upload_material', UPLOAD_REVOKED)),
        )
    ).all()
    return sum(row.points for row in rows), any(row.action == UPLOAD_REVOKED for row in rows)


def revoke_upload(db: Session, material: Material) -> int:
    """Take back upload XP when a material leaves the catalogue. Call before deleting the row."""
    uploader = db.get(User, material.uploader_id)
    if uploader is None:
        return 0
    _lock_users(db, uploader)
    held, _ = _upload_balance(db, uploader.user_id, material.material_id)
    if held <= 0:
        return 0
    return award_xp(db, uploader, UPLOAD_REVOKED, f'Removed "{material.title}"',
                    points=-held, material_id=material.material_id)


def restore_upload(db: Session, material: Material) -> int:
    """Pay upload XP again when a material that lost it comes back from Trash."""
    uploader = db.get(User, material.uploader_id)
    if uploader is None:
        return 0
    _lock_users(db, uploader)
    held, revoked = _upload_balance(db, uploader.user_id, material.material_id)
    if not revoked or held > 0:
        return 0
    return award_xp(db, uploader, 'upload_material', f'Restored "{material.title}"',
                    material_id=material.material_id)


def get_user_profile(db: Session, user: User) -> dict:
    # Ensure badges are up to date (e.g., if user already had uploads/2FA before gamification existed).
    if evaluate_badges(db, user):
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
    recent_rows = db.execute(
        select(XpEvent, Material.title)
        .outerjoin(Material, Material.material_id == XpEvent.material_id)
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
        'current_streak': effective_streak(user.current_streak, user.last_activity_date),
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
        'recent_events': [
            {
                'event_id': event.event_id,
                'action': event.action,
                'points': event.points,
                'description': event.description,
                'material_title': title,
                'created_at': event.created_at,
            }
            for event, title in recent_rows
        ],
    }


def get_leaderboard(db: Session, limit: int = 20) -> list[dict]:
    """Active students who have earned XP, best first. Admins and empty accounts are not ranked."""
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
            User.last_activity_date,
            func.coalesce(mat_sub.c.materials_count, 0).label('materials_count'),
            func.coalesce(mat_sub.c.total_downloads, 0).label('total_downloads'),
            func.coalesce(badge_sub.c.badges_count, 0).label('badges_count'),
        )
        .outerjoin(mat_sub, mat_sub.c.uid == User.user_id)
        .outerjoin(badge_sub, badge_sub.c.uid == User.user_id)
        .where(User.is_active.is_(True), User.role == 'student', User.xp_points > 0)
        .order_by(User.xp_points.desc(), func.coalesce(mat_sub.c.materials_count, 0).desc(), User.user_id.asc())
        .limit(limit)
    ).all()

    result = []
    today = local_today()
    for rank, row in enumerate(rows, start=1):
        level_info = compute_level(row.xp_points)
        result.append({
            'rank': rank,
            'user_id': row.user_id,
            'full_name': row.full_name,
            'xp_points': row.xp_points or 0,
            'level': level_info['level'],
            'level_code': level_info['level_code'],
            'current_streak': effective_streak(row.current_streak, row.last_activity_date, today),
            'materials_count': int(row.materials_count or 0),
            'total_downloads': int(row.total_downloads or 0),
            'badges_count': int(row.badges_count or 0),
        })
    return result


# --- Public student profiles -------------------------------------------------------------------

ACTIVITY_DAYS = 84  # 12 weeks shown as an activity heatmap
# What other people may not see on a profile: whether 2FA is on (it tells an attacker which
# accounts are easier targets) and which materials someone downloaded (what they study).
PRIVATE_BADGES = {'security_champion'}
PRIVATE_ACTIONS = {'enable_2fa'}
XP_GROUPS = {
    'upload_material': 'uploads',
    UPLOAD_REVOKED: 'uploads',
    'received_download': 'received_downloads',
    'download_material': 'downloads',
    'enable_2fa': 'security',
    'ai_study_session': 'ai_study',
}


def leaderboard_rank(db: Session, user: User) -> int | None:
    if user.role != 'student' or not user.is_active or (user.xp_points or 0) <= 0:
        return None
    ahead = db.scalar(
        select(func.count()).select_from(User)
        .where(User.is_active.is_(True), User.role == 'student', User.xp_points > user.xp_points)
    ) or 0
    return ahead + 1


def get_public_profile(db: Session, user_id: int, viewer: User | None = None) -> dict | None:
    """Gamification profile of any active student. The owner also sees their private details."""
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role != 'student':
        return None
    is_self = viewer is not None and viewer.user_id == user.user_id
    if evaluate_badges(db, user):
        db.commit()

    level_info = compute_level(user.xp_points)
    earned_map = {
        row.badge_code: row.earned_at
        for row in db.scalars(select(UserBadge).where(UserBadge.user_id == user.user_id)).all()
    }
    badges = [
        {'code': item['code'], 'icon': item['icon'], 'earned': item['code'] in earned_map,
         'earned_at': earned_map.get(item['code'])}
        for item in BADGE_CATALOG
        if is_self or item['code'] not in PRIVATE_BADGES
    ]

    breakdown: dict[str, int] = {}
    for action, points in db.execute(
        select(XpEvent.action, func.sum(XpEvent.points))
        .where(XpEvent.user_id == user.user_id)
        .group_by(XpEvent.action)
    ).all():
        if not is_self and action in PRIVATE_ACTIONS:
            continue
        group = XP_GROUPS.get(action, 'other')
        breakdown[group] = breakdown.get(group, 0) + int(points or 0)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=ACTIVITY_DAYS)
    days: dict[date, dict] = {}
    for created_at, points in db.execute(
        select(XpEvent.created_at, XpEvent.points)
        .where(XpEvent.user_id == user.user_id, XpEvent.created_at >= since, XpEvent.points > 0)
    ).all():
        day = local_today(created_at)
        entry = days.setdefault(day, {'date': day, 'xp': 0, 'actions': 0})
        entry['xp'] += points
        entry['actions'] += 1

    uploads = db.execute(
        select(Material.material_id, Material.title, Material.download_count, Material.uploaded_at,
               Course.course_code, Course.course_name, Category.category_name)
        .join(Course, Course.course_id == Material.course_id)
        .join(Category, Category.category_id == Material.category_id)
        .where(Material.uploader_id == user.user_id, Material.deleted_at.is_(None))
        .order_by(Material.material_id.desc())
    ).all()

    event_query = (
        select(XpEvent, Material.title)
        .outerjoin(Material, Material.material_id == XpEvent.material_id)
        .where(XpEvent.user_id == user.user_id)
    )
    if not is_self:
        event_query = event_query.where(XpEvent.action.not_in(PRIVATE_ACTIONS))
    events = []
    for event, title in db.execute(event_query.order_by(XpEvent.event_id.desc()).limit(30)).all():
        hide_title = not is_self and event.action == 'download_material'
        events.append({
            'event_id': event.event_id,
            'action': event.action,
            'points': event.points,
            'description': 'Studied a material' if hide_title else event.description,
            'material_title': None if hide_title else title,
            'created_at': event.created_at,
        })

    return {
        'user_id': user.user_id,
        'full_name': user.full_name,
        'is_self': is_self,
        'rank': leaderboard_rank(db, user),
        'xp_points': user.xp_points or 0,
        **level_info,
        'current_streak': effective_streak(user.current_streak, user.last_activity_date),
        'longest_streak': user.longest_streak or 0,
        'last_active_on': user.last_activity_date,
        'materials_count': len(uploads),
        'total_downloads_received': sum(int(row.download_count or 0) for row in uploads),
        'students_reached': db.scalar(
            select(func.count()).select_from(XpEvent)
            .where(XpEvent.user_id == user.user_id, XpEvent.action == 'received_download')
        ) or 0,
        'materials_studied': db.scalar(
            select(func.count()).select_from(XpEvent)
            .where(XpEvent.user_id == user.user_id, XpEvent.action == 'download_material')
        ) or 0,
        'badges': badges,
        'xp_breakdown': [{'source': key, 'xp': value} for key, value in sorted(breakdown.items(), key=lambda kv: -kv[1])],
        'activity_days': sorted(days.values(), key=lambda entry: entry['date']),
        'activity_window_days': ACTIVITY_DAYS,
        'today': local_today(now),
        'uploads': [
            {'material_id': row.material_id, 'title': row.title, 'download_count': int(row.download_count or 0),
             'uploaded_at': row.uploaded_at, 'course_code': row.course_code, 'course_name': row.course_name,
             'category_name': row.category_name}
            for row in uploads[:20]
        ],
        'recent_events': events,
    }
