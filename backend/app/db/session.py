from functools import lru_cache
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from ..core.config import settings

@lru_cache(maxsize=2)
def engine_for(url: str):
    if make_url(url).drivername != 'postgresql+psycopg':
        raise ValueError('DATABASE_URL must use postgresql+psycopg')
    return create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 5}, hide_parameters=True)

def get_db():
    if not settings.database_url:
        raise HTTPException(503, 'Database is not configured')
    with Session(engine_for(settings.database_url)) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
