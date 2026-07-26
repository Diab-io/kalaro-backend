from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Notification(TimeStampedModel):
    class Type(models.TextChoices):
        PAYMENT_APPROVED = "payment_approved", _("Payment approved")
        PAYMENT_REJECTED = "payment_rejected", _("Payment rejected")
        ENROLLMENT_GRANTED = "enrollment_granted", _("Enrolled in course")
        QUIZ_GRADED = "quiz_graded", _("Quiz graded")
        ASSIGNMENT_GRADED = "assignment_graded", _("Assignment graded")
        INSTRUCTOR_INVITE = "instructor_invite", _("Instructor invitation")
        CLASS_REMINDER = "class_reminder", _("Live class reminder")
        GENERAL = "general", _("General")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notifications")
    type = models.CharField(max_length=30, choices=Type.choices, default=Type.GENERAL)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)  # frontend route, e.g. /courses/5
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"])]
