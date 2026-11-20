from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.entities import Category, Course, Material, User
from ...schemas.admin import (
    AdminUser,
    AdminUserList,
    AgentConfigResponse,
    AgentConfigUpdate,
    BackupItem,
    BackupListResponse,
    BackupScheduleStatus,
    BackupScheduleUpdate,
    CategoryCreate,
    CourseCreate,
    CourseReport,
    DownloadReport,
    StorageCheck,
    UserChange,
)
from ...schemas.materials import CategoryResponse, CourseResponse
from ...services import backup, backup_scheduler, chatbot
from ...services.reconcile import scan
from ..dependencies import require_admin


class Overview(BaseModel):
    total_users: int
    total_materials: int


router = APIRouter(prefix='/admin', tags=['admin'], dependencies=[Depends(require_admin)])


@router.get('/overview', response_model=Overview)
def overview(db: Session = Depends(get_db)):
    return Overview(
        total_users=db.scalar(select(func.count()).select_from(User)),
        total_materials=db.scalar(
            select(func.count()).select_from(Material).where(Material.deleted_at.is_(None))
        ),
    )


@router.get('/users', response_model=AdminUserList)
def users(q: str = Query('', max_length=200), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
          db: Session = Depends(get_db)):
    query = select(User)
    if q.strip():
        query = query.where(or_(User.full_name.icontains(q.strip(), autoescape=True),
                                User.email.icontains(q.strip(), autoescape=True)))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(User.user_id).limit(limit).offset(offset)).all()
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}


@router.patch('/users/{user_id}', response_model=AdminUser)
def change_user(body: UserChange, user_id: int = Path(..., gt=0), admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, 'User not found')
    if target.user_id == admin.user_id:
        raise HTTPException(409, 'Administrators cannot change their own account here')
    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active
    db.commit()
    db.refresh(target)
    return target


@router.get('/reports/courses', response_model=CourseReport)
def course_report(db: Session = Depends(get_db)):
    count = func.count(Material.material_id)
    rows = db.execute(
        select(Course.course_id, Course.course_name, Course.course_code, count.label('material_count'))
        .outerjoin(Material, (Material.course_id == Course.course_id) & (Material.deleted_at.is_(None)))
        .group_by(Course.course_id)
        .order_by(count, Course.course_name)
    ).all()
    return {'items': [row._mapping for row in rows]}


@router.get('/reports/downloads', response_model=DownloadReport)
def download_report(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Material.material_id, Material.title, Course.course_name, Material.download_count)
        .join(Course)
        .where(Material.deleted_at.is_(None))
        .order_by(Material.download_count.desc(), Material.material_id)
        .limit(limit)
    ).all()
    total = db.scalar(
        select(func.coalesce(func.sum(Material.download_count), 0)).where(Material.deleted_at.is_(None))
    )
    return {'items': [row._mapping for row in rows], 'total_downloads': total}


@router.get('/storage-check', response_model=StorageCheck)
def storage_check(db: Session = Depends(get_db)):
    return {name: len(files) for name, files in scan(db).items()}


def add_unique(db, record, message):
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, message) from None
    db.refresh(record)
    return record


@router.post('/categories', response_model=CategoryResponse, status_code=201)
def add_category(body: CategoryCreate, db: Session = Depends(get_db)):
    return add_unique(db, Category(**body.model_dump()), 'Category already exists')


@router.post('/courses', response_model=CourseResponse, status_code=201)
def add_course(body: CourseCreate, db: Session = Depends(get_db)):
    return add_unique(db, Course(**body.model_dump()), 'Course code already exists')


# --- Scheduled Backups ---

@router.get('/backups', response_model=BackupListResponse)
def list_backups_admin(db: Session = Depends(get_db)):
    cfg = backup_scheduler.load_schedule_config(db)
    return {
        'schedule': backup_scheduler.scheduler.status_dict(cfg),
        'items': backup_scheduler.list_backup_summaries(),
    }


@router.patch('/backups/schedule', response_model=BackupScheduleStatus)
def update_backup_schedule(body: BackupScheduleUpdate, db: Session = Depends(get_db)):
    saved = backup_scheduler.save_schedule_config(db, body.model_dump(exclude_none=True))
    return backup_scheduler.scheduler.status_dict(saved)


@router.post('/backups/run', response_model=BackupItem, status_code=201)
def run_backup_now(db: Session = Depends(get_db)):
    cfg = backup_scheduler.load_schedule_config(db)
    bind_url = db.get_bind().url.render_as_string(hide_password=False)
    try:
        return backup_scheduler.scheduler.run_now(db_url=bind_url, keep=cfg['keep'])
    except backup.BackupError as error:
        raise HTTPException(503, str(error)) from None


# --- AI Agent Configuration ---

@router.get('/agent', response_model=AgentConfigResponse)
def get_agent_config(db: Session = Depends(get_db)):
    cfg = chatbot.load_agent_config(db)
    return {
        'api_key_configured': chatbot.enabled(),
        'provider': chatbot.active_provider() or 'none',
        **cfg,
        'default_system_prompt': chatbot.DEFAULT_SYSTEM_PROMPT,
        'available_tools': list(chatbot.ALL_TOOL_NAMES),
    }


@router.patch('/agent', response_model=AgentConfigResponse)
def update_agent_config(body: AgentConfigUpdate, db: Session = Depends(get_db)):
    updates = body.model_dump(exclude_none=True)
    if 'enabled_tools' in updates:
        unknown = [t for t in updates['enabled_tools'] if t not in chatbot.TOOL_DEFINITIONS]
        if unknown:
            raise HTTPException(422, f'Unknown agent tools: {", ".join(unknown)}')
    cfg = chatbot.save_agent_config(db, updates)
    return {
        'api_key_configured': chatbot.enabled(),
        'provider': chatbot.active_provider() or 'none',
        **cfg,
        'default_system_prompt': chatbot.DEFAULT_SYSTEM_PROMPT,
        'available_tools': list(chatbot.ALL_TOOL_NAMES),
    }
