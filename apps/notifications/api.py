from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from apps.accounts.auth import any_user

from .models import Notification
from .schemas import NotificationOut

router = Router(tags=["notifications"])


@router.get("", response=list[NotificationOut], auth=any_user)
def list_notifications(request, unread_only: bool = False):
    qs = request.auth.notifications.all()
    if unread_only:
        qs = qs.filter(read_at__isnull=True)
    return qs[:50]


@router.get("/unread-count", auth=any_user)
def unread_count(request):
    return {"count": request.auth.notifications.filter(read_at__isnull=True).count()}


@router.post("/{notification_id}/read", auth=any_user)
def mark_read(request, notification_id: int):
    n = get_object_or_404(Notification, pk=notification_id, user=request.auth)
    if not n.read_at:
        n.read_at = timezone.now()
        n.save(update_fields=["read_at"])
    return {"status": "read"}


@router.post("/read-all", auth=any_user)
def mark_all_read(request):
    request.auth.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return {"status": "ok"}