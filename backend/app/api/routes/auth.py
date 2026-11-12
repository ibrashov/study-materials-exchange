from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.entities import User
from ...schemas.auth import (LoginRequest, RegisterRequest, UserResponse, TokenResponse,
                             TwoFactorSetup, TwoFactorCode, TwoFactorDisable, TwoFactorStatus)
from ...core.config import settings
from ...services import twofactor
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
    if not user.is_active:
        raise HTTPException(403, 'Account is disabled')
    if user.totp_enabled:
        if not body.otp:
            raise HTTPException(401, 'otp_required')
        if not twofactor.verify_code(twofactor.decrypt(user.totp_secret or ''), body.otp):
            raise HTTPException(401, 'otp_invalid')
    elif settings.require_admin_2fa and user.role == 'admin':
        raise HTTPException(403, 'Administrator accounts must enable two-factor authentication first')
    return TokenResponse(access_token=create_token(user.user_id))

@router.get('/me', response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user


# --- Week 11 (Arnur): two-factor authentication (TOTP) -------------------------------------
@router.post('/2fa/setup', response_model=TwoFactorSetup)
def twofa_setup(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Create a fresh secret (not active until confirmed with a valid code)."""
    if user.totp_enabled:
        raise HTTPException(409, 'Two-factor authentication is already enabled')
    shared = twofactor.new_secret()
    user.totp_secret = twofactor.encrypt(shared)
    db.commit()
    return TwoFactorSetup(secret=shared, otpauth_uri=twofactor.provisioning_uri(shared, user.email))

@router.post('/2fa/enable', response_model=TwoFactorStatus)
def twofa_enable(body: TwoFactorCode, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.totp_enabled:
        raise HTTPException(409, 'Two-factor authentication is already enabled')
    if not user.totp_secret or not twofactor.verify_code(twofactor.decrypt(user.totp_secret), body.code):
        raise HTTPException(401, 'otp_invalid')
    user.totp_enabled = True
    db.commit()
    return TwoFactorStatus(enabled=True)

@router.post('/2fa/disable', response_model=TwoFactorStatus)
def twofa_disable(body: TwoFactorDisable, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not user.totp_enabled:
        raise HTTPException(409, 'Two-factor authentication is not enabled')
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(403, 'Password is incorrect')
    if not twofactor.verify_code(twofactor.decrypt(user.totp_secret or ''), body.code):
        raise HTTPException(401, 'otp_invalid')
    user.totp_enabled = False
    user.totp_secret = None
    db.commit()
    return TwoFactorStatus(enabled=False)
