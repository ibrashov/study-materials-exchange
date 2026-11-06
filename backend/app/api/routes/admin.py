from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.entities import User, Material
from ..dependencies import require_admin

class Overview(BaseModel):
    total_users: int
    total_materials: int

router = APIRouter(prefix='/admin', tags=['admin'], dependencies=[Depends(require_admin)])

@router.get('/overview', response_model=Overview)
def overview(db: Session = Depends(get_db)):
    return Overview(total_users=db.scalar(select(func.count()).select_from(User)),
                    total_materials=db.scalar(select(func.count()).select_from(Material)))
