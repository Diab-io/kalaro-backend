from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.accounts.auth import admin, any_user, instructor

from .models import Course, Lesson, Module
from .permissions import check_course_owner
from .schemas import (
    CourseCreateIn,
    CourseDetailOut,
    CourseListOut,
    CourseUpdateIn,
    LessonIn,
    ModuleIn,
    ReorderIn,
)
from .video import create_stream_upload

router = Router(tags=["catalog"])


# ---------------- public / student browsing ----------------

@router.get("/courses", response=list[CourseListOut], auth=None)
def list_courses(request):
    return Course.objects.filter(status=Course.Status.PUBLISHED)


@router.get("/courses/{slug}", response=CourseDetailOut, auth=None)
def get_course(request, slug: str):
    course = get_object_or_404(
        Course.objects.prefetch_related("modules__lessons"),
        slug=slug,
        status=Course.Status.PUBLISHED,
    )
    return course


@router.get("/courses/recommended", response=list[CourseListOut], auth=any_user)
def recommended_courses(request):
    profile = getattr(request.auth, "profile", None)
    qs = Course.objects.filter(status=Course.Status.PUBLISHED)
    if profile and profile.current_role:
        qs = qs.filter(target_roles__contains=profile.current_role)
    return qs[:10]


# ---------------- instructor authoring ----------------

@router.post("/courses", response={201: CourseDetailOut}, auth=instructor)
def create_course(request, payload: CourseCreateIn):
    course = Course.objects.create(instructor=request.auth, **payload.dict())
    return 201, course


@router.get("/instructor/courses", response=list[CourseListOut], auth=instructor)
def my_courses(request):
    qs = Course.objects.all()
    if request.auth.role != "admin":
        qs = qs.filter(instructor=request.auth)
    return qs


@router.patch("/courses/{course_id}", response=CourseDetailOut, auth=instructor)
def update_course(request, course_id: int, payload: CourseUpdateIn):
    course = get_object_or_404(Course, pk=course_id)
    check_course_owner(request.auth, course)

    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(course, field, value)
    course.save()
    return course


@router.post("/courses/{course_id}/publish", response=CourseDetailOut, auth=instructor)
def publish_course(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id)
    check_course_owner(request.auth, course)

    if not course.modules.exists():
        raise HttpError(400, "A course needs at least one module before it can be published.")
    course.status = Course.Status.PUBLISHED
    course.save(update_fields=["status"])
    return course


# ---------------- modules ----------------

@router.post("/courses/{course_id}/modules", response={201: dict}, auth=instructor)
def add_module(request, course_id: int, payload: ModuleIn):
    course = get_object_or_404(Course, pk=course_id)
    check_course_owner(request.auth, course)
    module = Module.objects.create(course=course, **payload.dict())
    return 201, {"id": module.id, "title": module.title, "order": module.order}


@router.patch("/modules/{module_id}/reorder", response={200: dict}, auth=instructor)
@transaction.atomic
def reorder_modules(request, module_id: int, payload: ReorderIn):
    # module_id here identifies the course via any one module in it,
    # simplest is to look up the course directly instead — left explicit:
    first = get_object_or_404(Module, pk=payload.ordered_ids[0])
    check_course_owner(request.auth, first.course)

    for index, mid in enumerate(payload.ordered_ids):
        Module.objects.filter(pk=mid, course=first.course).update(order=index)
    return {"status": "reordered"}


# ---------------- lessons ----------------

@router.post("/modules/{module_id}/lessons", response={201: dict}, auth=instructor)
def add_lesson(request, module_id: int, payload: LessonIn):
    module = get_object_or_404(Module, pk=module_id)
    check_course_owner(request.auth, module.course)
    lesson = Lesson.objects.create(module=module, **payload.dict())
    return 201, {"id": lesson.id, "title": lesson.title}


@router.patch("/lessons/{lesson_id}/reorder", response={200: dict}, auth=instructor)
@transaction.atomic
def reorder_lessons(request, lesson_id: int, payload: ReorderIn):
    first = get_object_or_404(Lesson, pk=payload.ordered_ids[0])
    check_course_owner(request.auth, first.module.course)

    for index, lid in enumerate(payload.ordered_ids):
        Lesson.objects.filter(pk=lid, module=first.module).update(order=index)
    return {"status": "reordered"}


# ---------------- admin ----------------

@router.get("/admin/courses", response=list[CourseListOut], auth=admin)
def admin_list_all_courses(request, status: str | None = None):
    qs = Course.objects.all()
    if status:
        qs = qs.filter(status=status)
    return qs

@router.post("/lessons/{lesson_id}/video-upload-url", auth=instructor)
def get_video_upload_url(request, lesson_id: int):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    check_course_owner(request.auth, lesson.module.course)

    upload = create_stream_upload(title=lesson.title)
    lesson.video_provider_id = upload["video_id"]
    lesson.save(update_fields=["video_provider_id"])

    return {
        "video_id": upload["video_id"],
        "upload_url": upload["upload_url"],
    }
