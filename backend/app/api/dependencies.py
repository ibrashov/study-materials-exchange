from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..models.entities import User
from ..services.auth import token_user_id

bearer = HTTPBearer(auto_error=False)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if credentials is None:
        raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    user = db.get(User, token_user_id(credentials.credentials))
    if user is None:
        raise HTTPException(401, 'Invalid or expired token')
    if not user.is_active:
        raise HTTPException(403, 'Account is disabled')
    return user

def require_student(user: User = Depends(current_user)):
    if user.role != 'student':
        raise HTTPException(403, 'Student role required')
    return user

def require_admin(user: User = Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Admin role required')
    return user
