from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.notifications.services import notify
from apps.payments.models import Enrollment
from .models import LiveSession


@shared_task
def send_class_reminders():
    now = timezone.now()
    windows = [(timedelta(hours=24), "24h"), (timedelta(hours=1), "1h")]

    for delta, label in windows:
        target_start = now + delta
        sessions = LiveSession.objects.filter(
            status=LiveSession.Status.SCHEDULED,
            scheduled_at__range=(target_start - timedelta(minutes=5), target_start + timedelta(minutes=5)),
        )
        for session in sessions:
            for enrollment in Enrollment.objects.filter(course=session.course, status="active"):
                notify(
                    user=enrollment.user, type="class_reminder",
                    title=f"Reminder: {session.title} starts soon",
                    body=f"Your class starts in {label}.",
                    link=f"/courses/{session.course.slug}/live/{session.id}",
                )