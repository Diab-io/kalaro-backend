import hashlib
import secrets
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Role(models.TextChoices):
    STUDENT = "student", _("Student")
    INSTRUCTOR = "instructor", _("Instructor")
    ADMIN = "admin", _("Administrator")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()   # Google-only accounts
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role", Role.STUDENT)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("email_verified", True)
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT,
                            db_index=True)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_instructor(self):
        return self.role == Role.INSTRUCTOR

    @property
    def is_platform_admin(self):
        return self.role == Role.ADMIN


class SocialAccount(TimeStampedModel):
    """One row per (provider, grant) so an instructor can hold both a
    sign-in grant and a Calendar grant from the same Google account."""

    class Provider(models.TextChoices):
        GOOGLE = "google", _("Google")

    class Purpose(models.TextChoices):
        SIGN_IN = "sign_in", _("Sign in")
        CALENDAR = "calendar", _("Calendar / Meet")

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE,
                             related_name="social_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    purpose = models.CharField(max_length=20, choices=Purpose.choices,
                               default=Purpose.SIGN_IN)
    provider_uid = models.CharField(max_length=255)  # Google 'sub'
    refresh_token = models.TextField(blank=True)      # only for calendar grant

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid", "purpose"],
                name="uniq_provider_uid_purpose",
            )
        ]


class OneTimeCode(TimeStampedModel):
    """Hashed OTP for email verification and password reset."""

    class Purpose(models.TextChoices):
        VERIFY_EMAIL = "verify_email", _("Verify email")
        RESET_PASSWORD = "reset_password", _("Reset password")

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE,
                             related_name="codes")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["user", "purpose", "consumed_at"])]

    @staticmethod
    def _hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, user, purpose, ttl_minutes=10):
        # invalidate any live codes of the same purpose first
        cls.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True).update(
            consumed_at=timezone.now()
        )
        raw = f"{secrets.randbelow(1_000_000):06d}"  # 6-digit, zero-padded
        cls.objects.create(
            user=user,
            purpose=purpose,
            code_hash=cls._hash(raw),
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return raw  # returned once, to be emailed, never stored raw

    @property
    def is_valid(self):
        return (
            self.consumed_at is None
            and self.attempts < 5
            and timezone.now() < self.expires_at
        )


class Profile(TimeStampedModel):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE,
                                related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)


class InstructorInvite(TimeStampedModel):
    email = models.EmailField(db_index=True)
    token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    invited_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                   null=True, related_name="sent_invites")
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    @property
    def is_valid(self):
        return self.accepted_at is None and timezone.now() < self.expires_at
