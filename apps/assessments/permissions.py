from ninja.errors import HttpError

from apps.catalog.permissions import check_enrolled, check_course_owner


def check_quiz_access(user, quiz):
    check_course_owner_or_enrolled(user, quiz.lesson.module.course)


def check_course_owner_or_enrolled(user, course):
    if user.role in ("instructor", "admin"):
        check_course_owner(user, course)
    else:
        check_enrolled(user, course)