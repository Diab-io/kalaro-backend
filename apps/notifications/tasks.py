from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


@shared_task
def send_notification_email(notification_id: int) -> None:
    n = Notification.objects.filter(pk=notification_id).select_related("user").first()
    if not n:
        return

    body = n.body
    if n.link:
        body += f"\n\nView it here: {settings.FRONTEND_BASE_URL}{n.link}"

    send_mail(
        subject=n.title,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[n.user.email],
    )