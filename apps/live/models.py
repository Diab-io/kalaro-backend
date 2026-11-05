from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Course
from apps.common.models import TimeStampedModel


class LiveSession(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="live_sessions")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="live_sessions")
    title = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    meet_link = models.URLField(blank=True)
    calendar_event_id = models.CharField(max_length=255, blank=True)
    recording_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        ordering = ["scheduled_at"]


class Attendance(TimeStampedModel):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="attendees")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="live_attendance")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "user"], name="uniq_session_attendance")
        ]


class GoogleCalendarGrant(TimeStampedModel):
    """Separate from accounts.SocialAccount's sign-in grant — this is the
    calendar.events consent, with a refresh token, requested independently."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="calendar_grant")
    refresh_token = models.TextField()
    calendar_id = models.CharField(max_length=255, default="primary")