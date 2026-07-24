import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Course
from apps.common.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name="orders")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="orders")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING,
                              db_index=True)
    reference = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class Payment(TimeStampedModel):
    class Provider(models.TextChoices):
        PAYSTACK = "paystack", _("Paystack")
        MANUAL = "manual", _("Manual bank transfer")

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_reference = models.CharField(max_length=150, unique=True, db_index=True)
    status = models.CharField(max_length=20, default="pending")
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ManualPayment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", _("Pending review")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="manual_payment")
    proof_file = models.FileField(upload_to="payment_proofs/")
    bank_reference = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PENDING_REVIEW)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="reviewed_payments")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True)


class Enrollment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        EXPIRED = "expired", _("Expired")
        REVOKED = "revoked", _("Revoked")

    class Source(models.TextChoices):
        PAYSTACK = "paystack", _("Paystack payment")
        MANUAL = "manual", _("Manual payment")
        ADMIN_GRANT = "admin_grant", _("Granted by admin")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="enrollments")
    source = models.CharField(max_length=20, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE,
                              db_index=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                condition=models.Q(status="active"),
                name="uniq_active_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.user_id} → {self.course_id} ({self.status})"