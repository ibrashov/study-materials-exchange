from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models.entities import User
from ...schemas.gamification import BadgeCatalogResponse, GamificationProfile, LeaderboardResponse
from ...services import gamification
from ..dependencies import current_user

router = APIRouter(prefix='/gamification', tags=['gamification'])


@router.get('/me', response_model=GamificationProfile)
def my_progress(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return gamification.get_user_profile(db, user)


@router.get('/leaderboard', response_model=LeaderboardResponse)
def leaderboard(limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    return {'items': gamification.get_leaderboard(db, limit=limit)}


@router.get('/badges', response_model=BadgeCatalogResponse)
def badge_catalog():
    return {'items': list(gamification.BADGE_CATALOG)}
