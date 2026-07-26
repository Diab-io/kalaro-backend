from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError

from .models import Answer, QuizAttempt
from apps.notifications.services import notify


@transaction.atomic
def submit_quiz_attempt(attempt: QuizAttempt) -> QuizAttempt:
    if attempt.status != QuizAttempt.Status.IN_PROGRESS:
        raise HttpError(409, "This attempt has already been submitted.")

    answers = attempt.answers.select_related("question")
    total_points = sum(a.question.points for a in answers)
    earned_points = 0
    has_ungraded_short_answer = False

    for answer in answers:
        if answer.question.type == "mcq":
            answer.is_correct = bool(
                answer.selected_choice and answer.selected_choice.is_correct
            )
            answer.points_awarded = answer.question.points if answer.is_correct else 0
            answer.save(update_fields=["is_correct", "points_awarded"])
            earned_points += answer.points_awarded
        else:
            has_ungraded_short_answer = True  # instructor grades this manually

    attempt.submitted_at = timezone.now()

    if has_ungraded_short_answer:
        attempt.status = QuizAttempt.Status.AWAITING_GRADING
        # score/passed stay null until instructor finishes grading
    else:
        attempt.score_percent = round((earned_points / total_points) * 100, 1) if total_points else 0
        attempt.passed = attempt.score_percent >= attempt.quiz.pass_percent
        attempt.status = QuizAttempt.Status.GRADED

    attempt.save()
    return attempt


@transaction.atomic
def grade_short_answers(attempt: QuizAttempt, scores: dict[int, float]) -> QuizAttempt:
    """scores: {answer_id: points_awarded}"""
    if attempt.status != QuizAttempt.Status.AWAITING_GRADING:
        raise HttpError(409, "This attempt is not awaiting grading.")

    for answer in attempt.answers.filter(question__type="short_answer"):
        if answer.id in scores:
            answer.points_awarded = scores[answer.id]
            answer.is_correct = scores[answer.id] >= answer.question.points
            answer.save(update_fields=["points_awarded", "is_correct"])

    total_points = sum(a.question.points for a in attempt.answers.select_related("question"))
    earned = sum(a.points_awarded for a in attempt.answers.all())

    attempt.score_percent = round((earned / total_points) * 100, 1) if total_points else 0
    attempt.passed = attempt.score_percent >= attempt.quiz.pass_percent
    attempt.status = QuizAttempt.Status.GRADED
    attempt.save()
    notify(
        user=attempt.user, type="quiz_graded",
        title="Your quiz has been graded",
        body=f"You scored {attempt.score_percent}% on {attempt.quiz.title}.",
        link=f"/quizzes/{attempt.quiz_id}/results",
    )
    return attempt