from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja.errors import HttpError

from apps.catalog.models import Course
from .models import Enrollment, Order
from apps.notifications.services import notify


@transaction.atomic
def grant_enrollment(*, user, course: Course, source: str, order: Order | None = None) -> Enrollment:
    """
    The ONLY place an Enrollment is ever created. Safe to call multiple
    times for the same user+course — the DB constraint makes duplicates
    a no-op rather than an error path we have to remember to handle.
    """
    if course.instructor_id == user.id:
        raise HttpError(400, "An instructor cannot be enrolled in their own course.")
    existing = Enrollment.objects.filter(
        user=user, course=course, status=Enrollment.Status.ACTIVE
    ).first()
    if existing:
        return existing  # idempotent — webhook retries land here safely

    try:
        enrollment = Enrollment.objects.create(
            user=user, course=course, order=order, source=source,
            status=Enrollment.Status.ACTIVE,
        )
    except IntegrityError:
        # Lost a race to a concurrent request — fetch what won.
        return Enrollment.objects.get(user=user, course=course,
                                      status=Enrollment.Status.ACTIVE)
    notify(
        user=user, type="enrollment_granted",
        title="You're enrolled!",
        body=f"You now have access to {course.title}.",
        link=f"/courses/{course.slug}",
    )
    return enrollment
