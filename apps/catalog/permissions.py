from ninja.errors import HttpError

from apps.accounts.models import Role
from apps.payments.models import Enrollment


def check_course_owner(user, course):
    if user.role == Role.ADMIN:
        return
    if course.instructor_id != user.id:
        raise HttpError(403, "You do not own this course.")

def check_enrolled(user, course):
    if user.role in ("instructor", "admin"):
        return  # instructors/admins bypass — ownership check happens separately
    is_enrolled = Enrollment.objects.filter(
        user=user, course=course, status=Enrollment.Status.ACTIVE
    ).exists()
    if not is_enrolled:
        raise HttpError(403, "You are not enrolled in this course.")
