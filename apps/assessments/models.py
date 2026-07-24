from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Course, Lesson
from apps.common.models import TimeStampedModel


# ---------------- quizzes ----------------

class Quiz(TimeStampedModel):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=200)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    pass_percent = models.PositiveSmallIntegerField(default=60)
    max_attempts = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    class Type(models.TextChoices):
        MCQ = "mcq", _("Multiple choice")
        SHORT_ANSWER = "short_answer", _("Short answer")

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.MCQ)
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]


class Choice(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class QuizAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", _("In progress")
        AWAITING_GRADING = "awaiting_grading", _("Awaiting grading")  # has short-answer parts
        GRADED = "graded", _("Graded")

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="quiz_attempts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score_percent = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True)

    class Meta:
        indexes = [models.Index(fields=["quiz", "user"])]


class Answer(TimeStampedModel):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True)  # null until graded (short answer)
    points_awarded = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="uniq_attempt_answer")
        ]


# ---------------- assignments ----------------

class Assignment(TimeStampedModel):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="assignment")
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    max_points = models.PositiveSmallIntegerField(default=100)

    def __str__(self):
        return self.title


class Submission(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", _("Submitted")
        GRADED = "graded", _("Graded")

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="submissions")
    file = models.FileField(upload_to="submissions/", blank=True, null=True)
    text_response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_late = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assignment", "user"], name="uniq_assignment_submission")
        ]


class Grade(TimeStampedModel):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="grade")
    points = models.FloatField()
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name="grades_given")
    graded_at = models.DateTimeField(auto_now_add=True)