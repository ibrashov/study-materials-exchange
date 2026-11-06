from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.entities import Category, Course, Material, User
from ...schemas.materials import MaterialList, MaterialResponse, CategoryList, CourseList
from ...services.storage import save_pdf, stored_path
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
    query = select(Material).join(Course).join(Category)
    if q.strip():
        query = query.where(or_(Material.title.icontains(q.strip(), autoescape=True),
                               Course.course_name.icontains(q.strip(), autoescape=True),
                               Category.category_name.icontains(q.strip(), autoescape=True)))
    if category_id:
        query = query.where(Material.category_id == category_id)
    if course_id:
        query = query.where(Material.course_id == course_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Material.material_id.desc()).limit(limit).offset(offset)).all()
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}

@router.post('/materials', response_model=MaterialResponse, status_code=201)
def upload(title: str = Form(..., min_length=1, max_length=200), category_id: int = Form(..., gt=0),
           course_id: int = Form(..., gt=0), file: UploadFile = File(...),
           user: User = Depends(require_student), db: Session = Depends(get_db)):
    title = title.strip()
    if not title or not db.get(Category, category_id) or not db.get(Course, course_id):
        raise HTTPException(422, 'Provide a title and existing category and course')
    name, size = save_pdf(file)
    material = Material(title=title, uploader_id=user.user_id, category_id=category_id,
                        course_id=course_id, file_path=name, file_size_bytes=size)
    try:
        db.add(material)
        db.flush()
        # Validate the public response before commit, so failures can still be rolled back.
        response = MaterialResponse.model_validate(material)
        db.commit()
        return response
    except BaseException as exc:
        db.rollback()
        stored_path(name).unlink(missing_ok=True)
        if isinstance(exc, IntegrityError):
            raise HTTPException(422, 'Invalid material references') from None
        raise

@router.get('/materials/{material_id}/download')
def download(material_id: int = Path(..., gt=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, 'Material not found')
    path = stored_path(material.file_path)
    if not path.is_file():
        raise HTTPException(404, 'File not found')
    return FileResponse(path, media_type='application/pdf', filename=f'material-{material_id}.pdf',
                        headers={'X-Content-Type-Options': 'nosniff'})
