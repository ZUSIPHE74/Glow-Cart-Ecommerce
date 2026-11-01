"""Django settings for ecommerce_project."""

from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", True)

# Never ship a usable default key: production must set DJANGO_SECRET_KEY.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or ("dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Set the DJANGO_SECRET_KEY environment variable.")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
# Render provides the service's public hostname.
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if DEBUG:
    ALLOWED_HOSTS += ["127.0.0.1", "localhost", "[::1]", "testserver"]
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in {"*", "testserver"}]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "ecommerce",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ecommerce_project.urls"

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
                "ecommerce.context_processors.shop",
            ],
        },
    },
]

WSGI_APPLICATION = "ecommerce_project.wsgi.application"
ASGI_APPLICATION = "ecommerce_project.asgi.application"


# A persistent Postgres (e.g. Neon) in production via DATABASE_URL. Without it the
# app falls back to a local SQLite file, which Render's free plan wipes on restart.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
# Neon's default connection string goes through a transaction pooler (PgBouncer).
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Africa/Johannesburg")
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@glowcart.example")

LOGIN_URL = "ecommerce:login"
LOGIN_REDIRECT_URL = "ecommerce:home"
LOGOUT_REDIRECT_URL = "ecommerce:login"

# Render terminates TLS at its proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"ecommerce": {"handlers": ["console"], "level": "INFO"}},
}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}


# ---- Marketplace ----
# Prices are stored and charged in rand; other currencies are shown converted.
BASE_CURRENCY = "ZAR"
# The marketplace's share of each sale; vendors are owed the rest.
MARKETPLACE_COMMISSION_PERCENT = os.getenv("MARKETPLACE_COMMISSION_PERCENT", "10")
# Unpaid orders hold their stock for this long, then are cancelled.
UNPAID_ORDER_TIMEOUT_MINUTES = int(os.getenv("UNPAID_ORDER_TIMEOUT_MINUTES", "60"))

# Shown on the contact, terms and privacy pages (required for real sales in SA).
SELLER_NAME = os.getenv("SELLER_NAME", "GlowCart Marketplace")
SELLER_EMAIL = os.getenv("SELLER_EMAIL", "support@glowcart.example")
SELLER_PHONE = os.getenv("SELLER_PHONE", "")
SELLER_ADDRESS = os.getenv("SELLER_ADDRESS", "")

# ---- PayFast ----
# Defaults are PayFast's shared sandbox merchant: test payments only, no real money.
# For full signature checks, create your own free sandbox account and set all three.
PAYFAST_SANDBOX = env_bool("PAYFAST_SANDBOX", True)
PAYFAST_MERCHANT_ID = os.getenv("PAYFAST_MERCHANT_ID", "10000100")
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_MERCHANT_KEY", "46f0cd694581a")
PAYFAST_PASSPHRASE = os.getenv("PAYFAST_PASSPHRASE", "")

# Public demo logins (shown on the login page). Off by default once payments are live;
# turning it off disables the demo accounts at the next deploy.
DEMO_ACCOUNTS = env_bool("DEMO_ACCOUNTS", PAYFAST_SANDBOX)
