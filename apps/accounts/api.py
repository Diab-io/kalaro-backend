from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle
from ninja import File
from ninja.files import UploadedFile

from .auth import admin, any_user
from .models import InstructorInvite, OneTimeCode, Profile, Role, User
from .schemas import (
    AcceptInviteIn,
    AdminUserCreateIn,
    GoogleAuthIn,
    InviteIn,
    InviteOut,
    LoginIn,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    ProfileUpdateIn,
    RegisterIn,
    ResendCodeIn,
    TokenOut,
    UserOut,
    VerifyEmailIn,
)
from .services import (
    consume_code,
    google_sign_in,
    issue_tokens,
    login_with_password,
    start_email_verification,
)
from .tasks import send_instructor_invite, send_otp_email

router = Router(tags=["auth"])

# Tight limits on anything that touches credentials or sends email.
credential_throttle = [AnonRateThrottle("10/m")]
otp_throttle = [AnonRateThrottle("5/m")]


# ---------------- registration and verification ----------------
@router.post("/register", response={201: MessageOut}, auth=None,
             throttle=credential_throttle)
def register(request, payload: RegisterIn):
    if not payload.agreed_to_terms:
        raise HttpError(400, "You must agree to the Terms of Service to continue.")

    email = payload.email.lower()
    if User.objects.filter(email=email).exists():
        raise HttpError(409, "An account with this email already exists.")

    user = User.objects.create_user(
        email=email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=Role.STUDENT,
    )
    Profile.objects.create(
        user=user,
        current_role=payload.current_role,
        experience_level=payload.experience_level,
        goal=payload.goal,
    )
    start_email_verification(user)
    return 201, {"detail": "Account created. Check your email for a verification code."}


@router.post("/verify-email", response=TokenOut, auth=None, throttle=otp_throttle)
def verify_email(request, payload: VerifyEmailIn):
    user = get_object_or_404(User, email=payload.email.lower())
    consume_code(user, payload.code, OneTimeCode.Purpose.VERIFY_EMAIL)
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
    return issue_tokens(user)


@router.post("/resend-code", response=MessageOut, auth=None, throttle=otp_throttle)
def resend_code(request, payload: ResendCodeIn):
    user = User.objects.filter(email=payload.email.lower()).first()
    if user and not user.email_verified:
        start_email_verification(user)
    # Always the same response, whether or not the account exists.
    return {"detail": "If that account needs verification, a code has been sent."}


@router.get("/registration-options", auth=None)
def registration_options(request):
    return {
        "current_roles": dict(Profile.CurrentRole.choices),
        "experience_levels": dict(Profile.ExperienceLevel.choices),
        "goals": dict(Profile.Goal.choices),
    }


# ---------------- login ----------------

@router.post("/login", response=TokenOut, auth=None, throttle=credential_throttle)
def login(request, payload: LoginIn):
    user = login_with_password(payload.email, payload.password)
    return issue_tokens(user)


@router.post("/google", response=TokenOut, auth=None, throttle=credential_throttle)
def google_auth(request, payload: GoogleAuthIn):
    user = google_sign_in(payload.id_token)
    return issue_tokens(user)


# ---------------- password reset ----------------

@router.post("/password-reset/request", response=MessageOut, auth=None,
             throttle=otp_throttle)
def password_reset_request(request, payload: PasswordResetRequestIn):
    user = User.objects.filter(email=payload.email.lower(), is_active=True).first()
    if user:
        raw = OneTimeCode.issue(user, OneTimeCode.Purpose.RESET_PASSWORD)
        send_otp_email.delay(user.pk, raw, OneTimeCode.Purpose.RESET_PASSWORD)
    return {"detail": "If that account exists, a reset code has been sent."}


@router.post("/password-reset/confirm", response=MessageOut, auth=None,
             throttle=otp_throttle)
def password_reset_confirm(request, payload: PasswordResetConfirmIn):
    user = get_object_or_404(User, email=payload.email.lower())
    consume_code(user, payload.code, OneTimeCode.Purpose.RESET_PASSWORD)
    user.set_password(payload.new_password)
    user.email_verified = True   # they proved control of the mailbox
    user.save(update_fields=["password", "email_verified"])
    return {"detail": "Password updated. You can now sign in."}


# ---------------- current user ----------------

@router.get("/me", response=UserOut, auth=any_user)
def me(request):
    user = request.auth
    profile = getattr(user, "profile", None)
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "email_verified": user.email_verified,
        "current_role": profile.current_role if profile else "",
        "experience_level": profile.experience_level if profile else "",
        "goal": profile.goal if profile else "",
        "avatar_url": profile.avatar.url if profile and profile.avatar else None,
    }


@router.post("/me/avatar", response=UserOut, auth=any_user)
def upload_avatar(request, avatar: UploadedFile = File(...)):
    user = request.auth
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.avatar = avatar
    profile.save(update_fields=["avatar"])
    return me(request)

@router.patch("/me", response=UserOut, auth=any_user)
def update_me(request, payload: ProfileUpdateIn):
    user = request.auth
    profile, _ = Profile.objects.get_or_create(user=user)

    data = payload.dict(exclude_unset=True)
    for field in ("first_name", "last_name"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
    user.save()

    for field in ("phone", "bio"):
        if field in data and data[field] is not None:
            setattr(profile, field, data[field])
    profile.save()
    return user

# ---------------- instructor onboarding ----------------

@router.post("/invites", response={201: InviteOut}, auth=admin)
def create_invite(request, payload: InviteIn):
    email = payload.email.lower()
    if User.objects.filter(email=email).exists():
        raise HttpError(409, "That email already has an account.")

    invite = InstructorInvite.objects.create(
        email=email,
        invited_by=request.auth,
        expires_at=str(timezone.now() + timedelta(days=7)),
    )
    send_instructor_invite.delay(invite.pk)
    return 201, invite


@router.post("/invites/accept", response=TokenOut, auth=None,
             throttle=credential_throttle)
@transaction.atomic
def accept_invite(request, payload: AcceptInviteIn):
    invite = InstructorInvite.objects.select_for_update().filter(
        token=payload.token
    ).first()
    if invite is None or not invite.is_valid:
        raise HttpError(400, "This invitation is invalid or has expired.")

    user = User.objects.create_user(
        email=invite.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=Role.INSTRUCTOR,
        email_verified=True,   # they received the token at that address
    )
    Profile.objects.create(user=user)
    invite.accepted_at = timezone.now()
    invite.save(update_fields=["accepted_at"])
    return issue_tokens(user)


# ---------------- admin user management ----------------

@router.post("/admin/users", response={201: UserOut}, auth=admin)
def admin_create_user(request, payload: AdminUserCreateIn):
    email = payload.email.lower()
    if User.objects.filter(email=email).exists():
        raise HttpError(409, "That email already has an account.")

    user = User.objects.create_user(
        email=email,
        password=None,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        email_verified=True,
    )
    Profile.objects.create(user=user)

    raw = OneTimeCode.issue(user, OneTimeCode.Purpose.RESET_PASSWORD)
    send_otp_email.delay(user.pk, raw, OneTimeCode.Purpose.RESET_PASSWORD)

    return 201, user


@router.get("/admin/users", response=list[UserOut], auth=admin)
def admin_list_users(request, role: str | None = None, search: str | None = None):
    qs = User.objects.all().order_by("-created_at")
    if role:
        qs = qs.filter(role=role)
    if search:
        qs = qs.filter(email__icontains=search)
    return qs


@router.patch("/admin/users/{user_id}", response=UserOut, auth=admin)
def admin_update_user(request, user_id: int, is_active: bool | None = None,
                      role: str | None = None):
    user = get_object_or_404(User, pk=user_id)
    if user.pk == request.auth.pk and is_active is False:
        raise HttpError(400, "You cannot deactivate your own account.")
    if is_active is not None:
        user.is_active = is_active
    if role is not None:
        user.role = role
    user.save()
    return user
