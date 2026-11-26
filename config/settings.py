import os
import secrets
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def local_key():
    path = BASE_DIR / ".local-secret"
    if not path.exists():
        temporary = path.with_suffix("." + secrets.token_hex(12))
        try:
            temporary.write_text(get_random_secret_key(), encoding="utf-8")
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    return path.read_text(encoding="utf-8").strip()


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or local_key()
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "drf_spectacular", "drf_spectacular_sidecar", "residencial",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
ROOT_URLCONF = "config.urls"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": os.getenv("SMARTCONNECT_DB") or BASE_DIR / "db.sqlite3",
                         "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 15}}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "America/Santiago"
LANGUAGE_CODE = "es-cl"
STATIC_URL = "static/"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {"TITLE": "SmartConnect · API residencial", "VERSION": "1.0.0",
                        "SWAGGER_UI_DIST": "SIDECAR", "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
                        "DESCRIPTION": "Catálogo, asignaciones y control de acceso. Horas ISO 8601.",
                        "SERVE_INCLUDE_SCHEMA": False, "COMPONENT_SPLIT_REQUEST": True}
