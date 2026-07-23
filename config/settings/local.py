from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)     # noqa: F405