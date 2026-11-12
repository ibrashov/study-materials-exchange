"""Week 11 (Arnur): TOTP (RFC 6238) helpers. Secrets are encrypted at rest with a key derived from AUTH_SECRET."""
import base64
import hashlib
import pyotp
from cryptography.fernet import Fernet, InvalidToken
from .auth import secret

ISSUER = 'Study Materials Exchange'

def _fernet():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'totp-v1:' + secret().encode()).digest()))

def new_secret():
    return pyotp.random_base32()

def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()

def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None

def provisioning_uri(shared_secret: str, email: str) -> str:
    return pyotp.TOTP(shared_secret).provisioning_uri(name=email, issuer_name=ISSUER)

def verify_code(shared_secret: str | None, code: str) -> bool:
    code = (code or '').strip().replace(' ', '')
    if not shared_secret or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(shared_secret).verify(code, valid_window=1)
