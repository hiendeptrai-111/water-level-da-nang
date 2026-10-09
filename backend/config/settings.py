"""Django settings. Every secret and environment-specific value is read from backend/.env
(see .env.example). Nothing secret is written in this file."""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Thiếu biến môi trường {name} (xem backend/.env.example)")
    return value


def env_bool(name, default=False):
    return str(env(name, str(default))).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [x.strip() for x in str(env(name, default)).split(",") if x.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "catalog",
    "accounts",
    "core",
    "reservoirs",
    "alerts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL only (no SQLite). Connection details come from .env.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "water_level"),
        "USER": env("DB_USER", "water"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "accounts.validators.LetterAndDigitValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------- DRF / JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_RATES": {
        "register": env("THROTTLE_REGISTER", "10/hour"),
        "login": env("THROTTLE_LOGIN", "30/minute"),
        "password_forgot": env("THROTTLE_PASSWORD_FORGOT", "5/hour"),
        "resend_verification": env("THROTTLE_RESEND_VERIFICATION", "5/hour"),
    },
    "NUM_PROXIES": 0,
}

# Lifetimes here are only fallbacks: the real values are read from SystemConfig
# (jwt_access_minutes, jwt_refresh_days) every time a token is issued.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_REFRESH_SERIALIZER": "accounts.serializers.TokenRefreshSerializer",
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# ---------------------------------------------------------------- Email
# Development: console backend (emails are printed in the terminal).
# Production: set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend and the SMTP vars.
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Canh bao lu Da Nang <no-reply@localhost>")

# Used to build links in emails (verify email, reset password).
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Forecast modules copied from the research folder (du_bao/, never edited).
FORECAST_DIR = Path(env("FORECAST_DIR", str(PROJECT_DIR / "du_bao")))
# Data store copied from the research folder (git-ignored): van_hanh/, mua_data/,
# ngoai_le_thu_cong.csv, plus raw Open-Meteo downloads in mua_tai_them/.
DATA_STORE_DIR = Path(env("DATA_STORE_DIR", str(PROJECT_DIR / "kho_du_lieu")))
# Sent with every request to the PCTT portal and Open-Meteo.
HTTP_USER_AGENT = env("HTTP_USER_AGENT",
                      "water-level-da-nang/2.0 (do an canh bao lu Da Nang; 1 lan/gio)")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
