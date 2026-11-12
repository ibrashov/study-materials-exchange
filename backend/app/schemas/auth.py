from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)
    otp: str | None = Field(default=None, max_length=12)

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

class RegisterRequest(LoginRequest):
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('full_name', mode='before')
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    full_name: str
    email: str
    role: Literal['student', 'admin']
    totp_enabled: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'

class TwoFactorSetup(BaseModel):
    secret: str
    otpauth_uri: str

class TwoFactorCode(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=6, max_length=12)

class TwoFactorDisable(TwoFactorCode):
    password: str = Field(min_length=1, max_length=128)

class TwoFactorStatus(BaseModel):
    enabled: bool
