from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.entities import User
from ...schemas.auth import LoginRequest, RegisterRequest, UserResponse, TokenResponse
from ...services.auth import hasher, verify_password, create_token, DUMMY_HASH
from ..dependencies import current_user

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/register', response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = User(full_name=body.full_name, email=str(body.email), password_hash=hasher.hash(body.password), role='student')
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.scalar(select(User.user_id).where(User.email == str(body.email))) is not None:
            raise HTTPException(409, 'Email is already registered') from None
        raise
    db.refresh(user)
    return user

@router.post('/login', response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email)))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not valid or user is None:
        raise HTTPException(401, 'Invalid email or password')
    return TokenResponse(access_token=create_token(user.user_id))

@router.get('/me', response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user
