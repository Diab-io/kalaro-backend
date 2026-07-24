from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja.errors import HttpError

from apps.catalog.models import Course
from .models import Enrollment, Order


@transaction.atomic
def grant_enrollment(*, user, course: Course, source: str, order: Order | None = None) -> Enrollment:
    """
    The ONLY place an Enrollment is ever created. Safe to call multiple
    times for the same user+course — the DB constraint makes duplicates
    a no-op rather than an error path we have to remember to handle.
    """
    existing = Enrollment.objects.filter(
        user=user, course=course, status=Enrollment.Status.ACTIVE
    ).first()
    if existing:
        return existing  # idempotent — webhook retries land here safely

    try:
        return Enrollment.objects.create(
            user=user, course=course, order=order, source=source,
            status=Enrollment.Status.ACTIVE,
        )
    except IntegrityError:
        # Lost a race to a concurrent request — fetch what won.
        return Enrollment.objects.get(user=user, course=course,
                                      status=Enrollment.Status.ACTIVE)