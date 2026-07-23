from ninja import Schema
from pydantic import EmailStr, Field


# ---- requests ----
class RegisterIn(Schema):
    email: EmailStr
    password: str = Field(min_length=10)
    first_name: str = ""
    last_name: str = ""


class VerifyEmailIn(Schema):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeIn(Schema):
    email: EmailStr


class LoginIn(Schema):
    email: EmailStr
    password: str


class GoogleAuthIn(Schema):
    id_token: str


class PasswordResetRequestIn(Schema):
    email: EmailStr


class PasswordResetConfirmIn(Schema):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=10)


class AcceptInviteIn(Schema):
    token: str
    password: str = Field(min_length=10)
    first_name: str = ""
    last_name: str = ""


class ProfileUpdateIn(Schema):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    bio: str | None = None


# ---- responses ----
class TokenOut(Schema):
    access: str
    refresh: str


class UserOut(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    email_verified: bool


class MessageOut(Schema):
    detail: str