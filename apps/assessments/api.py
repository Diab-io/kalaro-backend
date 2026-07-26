from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from apps.accounts.auth import any_user, instructor
from apps.catalog.models import Lesson
from apps.catalog.permissions import check_course_owner

from .grading import grade_short_answers, submit_quiz_attempt
from .models import Answer, Assignment, Choice, Grade, Question, Quiz, QuizAttempt, Submission
from .permissions import check_course_owner_or_enrolled
from .schemas import (
    AssignmentCreateIn,
    AttemptOut,
    GradeIn,
    GradeShortAnswersIn,
    QuestionIn,
    QuizCreateIn,
    QuizOut,
    SubmissionOut,
    SubmitAttemptIn,
)
from apps.notifications.services import notify

router = Router(tags=["assessments"])


# ---------------- quiz authoring ----------------

@router.post("/lessons/{lesson_id}/quiz", response={201: QuizOut}, auth=instructor)
def create_quiz(request, lesson_id: int, payload: QuizCreateIn):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    check_course_owner(request.auth, lesson.module.course)

    if hasattr(lesson, "quiz"):
        raise HttpError(409, "This lesson already has a quiz.")

    quiz = Quiz.objects.create(lesson=lesson, **payload.dict())
    return 201, quiz


@router.post("/quizzes/{quiz_id}/questions", response={201: dict}, auth=instructor)
def add_question(request, quiz_id: int, payload: QuestionIn):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    check_course_owner(request.auth, quiz.lesson.module.course)

    if payload.type == "mcq" and not any(c.is_correct for c in payload.choices):
        raise HttpError(400, "An MCQ question needs at least one correct choice.")

    question = Question.objects.create(
        quiz=quiz, text=payload.text, type=payload.type,
        order=payload.order, points=payload.points,
    )
    for c in payload.choices:
        Choice.objects.create(question=question, **c.dict())

    return 201, {"id": question.id}


# ---------------- quiz taking (student) ----------------

@router.get("/lessons/{lesson_id}/quiz", response=QuizOut, auth=any_user)
def get_quiz(request, lesson_id: int):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    check_course_owner_or_enrolled(request.auth, lesson.module.course)
    return get_object_or_404(Quiz, lesson=lesson)


@router.post("/quizzes/{quiz_id}/attempts", response={201: AttemptOut}, auth=any_user)
def start_attempt(request, quiz_id: int):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    check_course_owner_or_enrolled(request.auth, quiz.lesson.module.course)

    if request.auth.role in ("instructor", "admin"):
        raise HttpError(403, "Instructors cannot attempt quizzes.")

    existing_count = QuizAttempt.objects.filter(quiz=quiz, user=request.auth).count()
    if existing_count >= quiz.max_attempts:
        raise HttpError(409, "You have used all your attempts for this quiz.")

    attempt = QuizAttempt.objects.create(quiz=quiz, user=request.auth)
    return 201, attempt


@router.post("/attempts/{attempt_id}/submit", response=AttemptOut, auth=any_user)
def submit_attempt(request, attempt_id: int, payload: SubmitAttemptIn):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.auth)

    for a in payload.answers:
        Answer.objects.update_or_create(
            attempt=attempt, question_id=a.question_id,
            defaults={
                "selected_choice_id": a.selected_choice_id,
                "text_answer": a.text_answer,
            },
        )

    return submit_quiz_attempt(attempt)


@router.get("/my-attempts/{quiz_id}", response=list[AttemptOut], auth=any_user)
def my_attempts(request, quiz_id: int):
    return QuizAttempt.objects.filter(quiz_id=quiz_id, user=request.auth)


# ---------------- instructor grading (short answer) ----------------

@router.get("/quizzes/{quiz_id}/pending-grading", auth=instructor)
def pending_grading(request, quiz_id: int):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    check_course_owner(request.auth, quiz.lesson.module.course)
    attempts = QuizAttempt.objects.filter(quiz=quiz, status=QuizAttempt.Status.AWAITING_GRADING)
    return [{"attempt_id": a.id, "user_email": a.user.email} for a in attempts]


@router.post("/attempts/{attempt_id}/grade", response=AttemptOut, auth=instructor)
def grade_attempt(request, attempt_id: int, payload: GradeShortAnswersIn):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id)
    check_course_owner(request.auth, attempt.quiz.lesson.module.course)
    return grade_short_answers(attempt, payload.scores)


# ---------------- assignments ----------------

@router.post("/lessons/{lesson_id}/assignment", response={201: dict}, auth=instructor)
def create_assignment(request, lesson_id: int, payload: AssignmentCreateIn):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    check_course_owner(request.auth, lesson.module.course)
    if hasattr(lesson, "assignment"):
        raise HttpError(409, "This lesson already has an assignment.")
    assignment = Assignment.objects.create(lesson=lesson, **payload.dict())
    return 201, {"id": assignment.id}


@router.post("/assignments/{assignment_id}/submit", response={201: SubmissionOut}, auth=any_user)
def submit_assignment(request, assignment_id: int, text_response: str = "", file=None):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    check_course_owner_or_enrolled(request.auth, assignment.lesson.module.course)

    if request.auth.role in ("instructor", "admin"):
        raise HttpError(403, "Instructors cannot submit assignments.")

    is_late = bool(assignment.due_at and timezone.now() > assignment.due_at)

    submission, _ = Submission.objects.update_or_create(
        assignment=assignment, user=request.auth,
        defaults={"text_response": text_response, "file": file, "is_late": is_late},
    )
    return 201, submission


@router.post("/submissions/{submission_id}/grade", auth=instructor)
def grade_submission(request, submission_id: int, payload: GradeIn):
    submission = get_object_or_404(Submission, pk=submission_id)
    check_course_owner(request.auth, submission.assignment.lesson.module.course)

    Grade.objects.update_or_create(
        submission=submission,
        defaults={"points": payload.points, "feedback": payload.feedback,
                  "graded_by": request.auth},
    )
    submission.status = Submission.Status.GRADED
    submission.save(update_fields=["status"])

    notify(
        user=submission.user, type="assignment_graded",
        title="Your assignment has been graded",
        body=f"You scored {payload.points} on {submission.assignment.title}.",
        link=f"/assignments/{submission.assignment_id}/results",
    )
    return {"status": "graded"}