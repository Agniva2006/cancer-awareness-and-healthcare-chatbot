"""Pydantic schemas for the auth API."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=72)
    full_name: str = Field("", max_length=255)

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        from app.core.security import PasswordPolicyError, validate_password_strength

        try:
            validate_password_strength(v)
        except PasswordPolicyError as exc:
            raise ValueError(str(exc))
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token lifetime in seconds


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class UserWithUsage(UserOut):
    plan_code: str = "free"
    quota_used: int = 0
    quota_limit: int = 20


class MessageOut(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)
    new_password: str = Field(..., min_length=10, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        from app.core.security import PasswordPolicyError, validate_password_strength

        try:
            validate_password_strength(v)
        except PasswordPolicyError as exc:
            raise ValueError(str(exc))
        return v
