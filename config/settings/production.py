import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
AWS_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID")          # noqa: F405
AWS_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY")  # noqa: F405
AWS_STORAGE_BUCKET_NAME = env("R2_BUCKET")           # noqa: F405
AWS_S3_ENDPOINT_URL = env("R2_ENDPOINT_URL")         # noqa: F405
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None

if env("SENTRY_DSN", default=""):  # noqa: F405
    sentry_sdk.init(dsn=env("SENTRY_DSN"), integrations=[DjangoIntegration()])  # noqa: F405