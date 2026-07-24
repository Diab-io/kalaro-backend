from ninja.errors import HttpError

from apps.accounts.models import Role


def check_course_owner(user, course):
    if user.role == Role.ADMIN:
        return
    if course.instructor_id != user.id:
        raise HttpError(403, "You do not own this course.")