from ninja import Schema
from pydantic import EmailStr, Field


# ---- requests ----
class RegisterIn(Schema):
    email: EmailStr
    password: str = Field(min_length=10)
    first_name: str = ""
    last_name: str = ""
    current_role: str = ""
    experience_level: str = ""
    goal: str = ""
    agreed_to_terms: bool = False


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
    current_role: str = ""
    experience_level: str = ""
    goal: str = ""


class MessageOut(Schema):
    detail: str


class InviteIn(Schema):
    email: EmailStr


class InviteOut(Schema):
    id: int
    email: str
    expires_at: str


class AdminUserCreateIn(Schema):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    role: str = "instructor"
