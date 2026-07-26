from .models import Notification


def notify(*, user, type: str, title: str, body: str = "", link: str = "",
           send_email: bool = True) -> Notification:
    notification = Notification.objects.create(
        user=user, type=type, title=title, body=body, link=link,
    )
    if send_email:
        from .tasks import send_notification_email
        send_notification_email.delay(notification.id)
    return notification