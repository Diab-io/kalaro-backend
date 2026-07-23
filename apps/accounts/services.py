from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from ninja.errors import HttpError
from ninja_jwt.tokens import RefreshToken

from .models import OneTimeCode, Profile, Role, SocialAccount, User


def issue_tokens(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


# ---------- OTP ----------

def start_email_verification(user: User) -> None:
    from .tasks import send_otp_email
    raw = OneTimeCode.issue(user, OneTimeCode.Purpose.VERIFY_EMAIL)
    send_otp_email.delay(user.pk, raw, OneTimeCode.Purpose.VERIFY_EMAIL)


def consume_code(user: User, raw_code: str, purpose: str) -> None:
    """Raises HttpError on any failure. Never leaks which part failed."""
    code = (
        OneTimeCode.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if code is None:
        raise HttpError(400, "Invalid or expired code.")

    if not code.is_valid:
        raise HttpError(400, "Invalid or expired code.")

    if code.code_hash != OneTimeCode._hash(raw_code):
        OneTimeCode.objects.filter(pk=code.pk).update(attempts=code.attempts + 1)
        raise HttpError(400, "Invalid or expired code.")

    code.consumed_at = timezone.now()
    code.save(update_fields=["consumed_at"])


# ---------- password login ----------

def login_with_password(email: str, password: str) -> User:
    user = authenticate(username=email.lower(), password=password)
    if user is None:
        raise HttpError(401, "Invalid credentials.")
    if not user.is_active:
        raise HttpError(403, "Account is disabled.")
    if not user.email_verified:
        raise HttpError(403, "Email not verified.")
    return user


# ---------- Google ----------

def verify_google_id_token(raw_token: str) -> dict:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HttpError(503, "Google sign-in is not configured.")
    try:
        info = google_id_token.verify_oauth2_token(
            raw_token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except ValueError:
        raise HttpError(401, "Invalid Google token.")

    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HttpError(401, "Invalid Google token.")
    if not info.get("email"):
        raise HttpError(400, "Google account has no email.")
    return info


@transaction.atomic
def google_sign_in(raw_token: str) -> User:
    info = verify_google_id_token(raw_token)
    sub = info["sub"]
    email = info["email"].lower()
    google_verified = bool(info.get("email_verified"))

    # 1. Known Google identity
    social = (
        SocialAccount.objects.select_related("user")
        .filter(
            provider=SocialAccount.Provider.GOOGLE,
            provider_uid=sub,
            purpose=SocialAccount.Purpose.SIGN_IN,
        )
        .first()
    )
    if social:
        if not social.user.is_active:
            raise HttpError(403, "Account is disabled.")
        return social.user

    # 2. Existing local account with the same email
    user = User.objects.filter(email=email).first()
    if user:
        if not google_verified:
            raise HttpError(
                409,
                "An account with this email already exists. "
                "Sign in with your password, or verify your email with Google first.",
            )
        SocialAccount.objects.create(
            user=user,
            provider=SocialAccount.Provider.GOOGLE,
            provider_uid=sub,
            purpose=SocialAccount.Purpose.SIGN_IN,
        )
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        return user

    # 3. Brand new user
    user = User.objects.create_user(
        email=email,
        password=None,                      # unusable password
        first_name=info.get("given_name", ""),
        last_name=info.get("family_name", ""),
        role=Role.STUDENT,                  # Google sign-in never grants staff roles
        email_verified=google_verified,
    )
    Profile.objects.create(user=user)
    SocialAccount.objects.create(
        user=user,
        provider=SocialAccount.Provider.GOOGLE,
        provider_uid=sub,
        purpose=SocialAccount.Purpose.SIGN_IN,
    )
    return user