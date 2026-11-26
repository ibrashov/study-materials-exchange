from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.entities import Category, Course, Material, User
from ...schemas.materials import (
    CategoryList,
    CourseList,
    EmptyTrashResponse,
    MaterialList,
    MaterialResponse,
    TrashMaterialList,
    TrashMaterialResponse,
)
from ...services import gamification
from ...services.moderation import enforce_material_moderation
from ...services.title_validation import enforce_title_validation
from ...services.storage import download_stored, remove_stored, save_pdf
from ..dependencies import current_user, require_student

router = APIRouter(tags=['materials'])


@router.get('/categories', response_model=CategoryList)
def categories(db: Session = Depends(get_db)):
    return {'items': db.scalars(select(Category).order_by(Category.category_id)).all()}


@router.get('/courses', response_model=CourseList)
def courses(db: Session = Depends(get_db)):
    return {'items': db.scalars(select(Course).order_by(Course.course_id)).all()}


@router.get('/materials', response_model=MaterialList)
def materials(q: str = Query('', max_length=200), category_id: int | None = Query(None, gt=0),
              course_id: int | None = Query(None, gt=0), limit: int = Query(20, ge=1, le=100),
              offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    # Week 11 (Daryn): no joins; text search uses trigram indexes on each table, then ids.
    query = select(Material).where(Material.deleted_at.is_(None))
    term = q.strip()
    if term:
        # Resolve the (tiny) course/category tables first, so the big table sees plain id lists and
        # PostgreSQL can combine the trigram title index with the course/category indexes (BitmapOr).
        course_ids = db.scalars(select(Course.course_id).where(Course.course_name.icontains(term, autoescape=True))).all()
        category_ids = db.scalars(select(Category.category_id).where(Category.category_name.icontains(term, autoescape=True))).all()
        conditions = [Material.title.icontains(term, autoescape=True)]
        if course_ids:
            conditions.append(Material.course_id.in_(course_ids))
        if category_ids:
            conditions.append(Material.category_id.in_(category_ids))
        query = query.where(or_(*conditions))
    if category_id:
        query = query.where(Material.category_id == category_id)
    if course_id:
        query = query.where(Material.course_id == course_id)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = db.scalars(query.order_by(Material.material_id.desc()).limit(limit).offset(offset)).all()
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}


@router.get('/materials/trash', response_model=TrashMaterialList)
def list_trash(user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Material).where(Material.deleted_at.is_not(None))
    if user.role != 'admin':
        query = query.where(Material.uploader_id == user.user_id)
    items = db.scalars(query.order_by(Material.deleted_at.desc(), Material.material_id.desc())).all()
    return {'items': items, 'total': len(items)}


@router.delete('/materials/trash', response_model=EmptyTrashResponse)
def empty_trash(user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Material).where(Material.deleted_at.is_not(None))
    if user.role != 'admin':
        query = query.where(Material.uploader_id == user.user_id)
    items = db.scalars(query).all()
    names = [item.file_path for item in items]
    for item in items:
        db.delete(item)
    db.commit()
    for name in names:
        remove_stored(name)
    return {'deleted_count': len(names)}


@router.post('/materials', response_model=MaterialResponse, status_code=201)
def upload(title: str = Form(..., min_length=1, max_length=200), category_id: int = Form(..., gt=0),
           course_id: int = Form(..., gt=0), file: UploadFile = File(...),
           user: User = Depends(require_student), db: Session = Depends(get_db)):
    title = title.strip()
    if not title or not db.get(Category, category_id):
        raise HTTPException(422, 'Provide a title and existing category and course')
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(422, 'Provide a title and existing category and course')
    enforce_material_moderation(title=title, filename=file.filename)
    enforce_title_validation(title, course)
    name, size = save_pdf(file)
    material = Material(title=title, uploader_id=user.user_id, category_id=category_id,
                        course_id=course_id, file_path=name, file_size_bytes=size)
    try:
        db.add(material)
        db.flush()
        gamification.award_xp(db, user, 'upload_material', f'Uploaded "{title}"', material_id=material.material_id)
        # Validate the public response before commit, so failures can still be rolled back.
        response = MaterialResponse.model_validate(material)
        db.commit()
        return response
    except BaseException as exc:
        db.rollback()
        remove_stored(name)
        if isinstance(exc, IntegrityError):
            raise HTTPException(422, 'Invalid material references') from None
        raise


@router.get('/materials/{material_id}/download')
def download(material_id: int = Path(..., gt=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None or material.deleted_at is not None:
        raise HTTPException(404, 'Material not found')
    data = download_stored(material.file_path)
    db.execute(update(Material).where(Material.material_id == material_id)
               .values(download_count=Material.download_count + 1))
    gamification.reward_download(db, user, material)
    db.commit()
    headers = {'X-Content-Type-Options': 'nosniff'}
    if isinstance(data, bytes):
        headers['Content-Disposition'] = f'attachment; filename="material-{material_id}.pdf"'
        return Response(data, media_type='application/pdf', headers=headers)
    return FileResponse(data, media_type='application/pdf', filename=f'material-{material_id}.pdf', headers=headers)


@router.post('/materials/{material_id}/trash', response_model=TrashMaterialResponse)
def move_to_trash(material_id: int = Path(..., gt=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None or material.deleted_at is not None:
        raise HTTPException(404, 'Material not found')
    if user.role != 'admin' and material.uploader_id != user.user_id:
        raise HTTPException(403, 'Only the uploader or an administrator can move this material to trash')
    material.deleted_at = datetime.now(timezone.utc)
    material.deleted_by_id = user.user_id
    gamification.revoke_upload(db, material)
    db.commit()
    db.refresh(material)
    return material


@router.post('/materials/{material_id}/restore', response_model=MaterialResponse)
def restore_from_trash(material_id: int = Path(..., gt=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None or material.deleted_at is None:
        raise HTTPException(404, 'Material not found in trash')
    if user.role != 'admin' and material.uploader_id != user.user_id:
        raise HTTPException(403, 'Only the uploader or an administrator can restore this material')
    material.deleted_at = None
    material.deleted_by_id = None
    gamification.restore_upload(db, material)
    db.commit()
    db.refresh(material)
    return material


@router.delete('/materials/{material_id}', status_code=204)
def delete_material(
    material_id: int = Path(..., gt=0),
    trash: bool = Query(False),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, 'Material not found')
    if user.role != 'admin' and material.uploader_id != user.user_id:
        raise HTTPException(403, 'Only the uploader or an administrator can delete this material')
    if trash:
        if material.deleted_at is not None:
            raise HTTPException(404, 'Material not found')
        material.deleted_at = datetime.now(timezone.utc)
        material.deleted_by_id = user.user_id
        gamification.revoke_upload(db, material)
        db.commit()
        return
    name = material.file_path
    gamification.revoke_upload(db, material)
    db.delete(material)
    db.commit()
    remove_stored(name)
