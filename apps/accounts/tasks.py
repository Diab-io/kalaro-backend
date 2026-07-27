from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import InstructorInvite, OneTimeCode, User

SUBJECTS = {
    OneTimeCode.Purpose.VERIFY_EMAIL: "Verify your Kalaro Institute email",
    OneTimeCode.Purpose.RESET_PASSWORD: "Set your Kalaro Institute password",
}


@shared_task
def send_otp_email(user_id: int, raw_code: str, purpose: str) -> None:
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return

    if purpose == OneTimeCode.Purpose.VERIFY_EMAIL:
        message = (
            f"Hello {user.full_name},\n\n"
            f"Your verification code is: {raw_code}\n\n"
            f"Enter this code on the verification page to continue.\n\n"
            f"It expires in 10 minutes. If you did not request this, ignore this email."
        )
    else:
        link = f"{settings.FRONTEND_BASE_URL}/forgot-password?email={user.email}&code={raw_code}"
        message = (
            f"Hello {user.full_name},\n\n"
            f"Your code is: {raw_code}\n\n"
            f"Click here to continue: {link}\n\n"
            f"It expires in 10 minutes. If you did not request this, ignore this email."
        )

    send_mail(
        subject=SUBJECTS.get(purpose, "Your Kalaro Institute verification code"),
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task
def send_instructor_invite(invite_id: int) -> None:
    invite = InstructorInvite.objects.filter(pk=invite_id).first()
    if not invite:
        return
    link = f"{settings.FRONTEND_BASE_URL}/accept-invite?token={invite.token}"
    send_mail(
        subject="You have been invited to teach at Kalaro Institute",
        message=(
            f"You have been invited as an instructor.\n\n"
            f"Set up your account here: {link}\n\n"
            f"This invitation expires in 7 days."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.email],
    )