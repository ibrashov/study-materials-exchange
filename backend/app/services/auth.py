from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException
from ..core.config import settings

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash('unused login timing placeholder')

def secret():
    if len(settings.auth_secret) < 32 or settings.auth_secret.startswith('replace-'):
        raise HTTPException(503, 'Configure AUTH_SECRET with at least 32 random characters')
    return settings.auth_secret

def verify_password(password, password_hash):
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False

def create_token(user_id):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user_id), 'iat': now, 'exp': now + timedelta(minutes=settings.token_minutes),
                       'iss': 'study-materials-backend', 'aud': 'study-materials'}, secret(), algorithm='HS256')

def token_user_id(token):
    key = secret()
    try:
        claims = jwt.decode(token, key, algorithms=['HS256'], issuer='study-materials-backend',
                            audience='study-materials', options={'require': ['sub', 'iat', 'exp', 'iss', 'aud']})
        user_id = int(claims['sub'])
        if user_id < 1:
            raise ValueError('Invalid subject')
        return user_id
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(401, 'Invalid or expired token', headers={'WWW-Authenticate': 'Bearer'}) from None
