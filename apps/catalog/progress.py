from django.db import transaction
from django.utils import timezone

from .models import CourseProgress, Lesson, LessonProgress


@transaction.atomic
def mark_lesson_complete(*, user, lesson: Lesson) -> LessonProgress:
    progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    if not progress.completed_at:
        progress.completed_at = timezone.now()
        progress.save(update_fields=["completed_at"])

    _recompute_course_progress(user=user, course=lesson.module.course)
    return progress


def _recompute_course_progress(*, user, course):
    total = Lesson.objects.filter(module__course=course).count()
    if total == 0:
        return

    completed = LessonProgress.objects.filter(
        user=user, lesson__module__course=course, completed_at__isnull=False
    ).count()

    percent = round((completed / total) * 100)
    cp, _ = CourseProgress.objects.get_or_create(user=user, course=course)
    cp.percent = percent
    if percent == 100 and not cp.completed_at:
        cp.completed_at = timezone.now()
    cp.save()