from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Course(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    objectives = models.JSONField(default=list, blank=True)  # list[str]
    cover_image = models.ImageField(upload_to="course_covers/", blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="NGN")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT,
                              db_index=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="courses_taught")

    duration_weeks = models.PositiveSmallIntegerField(null=True, blank=True)

    # personalization targeting — see accounts.Profile choices
    target_roles = models.JSONField(default=list, blank=True)
    target_experience = models.JSONField(default=list, blank=True)
    target_goals = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "instructor"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Module(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "order"], name="uniq_module_order")
        ]

    def __str__(self):
        return f"{self.course.title} — {self.title}"


class Lesson(TimeStampedModel):
    class ContentType(models.TextChoices):
        VIDEO = "video", _("Video")
        TEXT = "text", _("Text")
        MIXED = "mixed", _("Mixed")

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=10, choices=ContentType.choices,
                                    default=ContentType.VIDEO)
    text_content = models.TextField(blank=True)
    video_provider_id = models.CharField(max_length=255, blank=True)  # Bunny/Cloudflare id
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["module", "order"], name="uniq_lesson_order")
        ]

    def __str__(self):
        return self.title


class Resource(TimeStampedModel):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="lesson_resources/")
    size_bytes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title