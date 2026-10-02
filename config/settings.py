"""Environment-based settings; PostgreSQL is required in every environment."""
import os
from ipaddress import ip_address
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Select the context before reading any local file. Production never reads .env.
ENVIRONMENT = os.environ.get("DJANGO_ENV", "development").strip().lower()
if ENVIRONMENT not in {"development", "production"}:
    raise ImproperlyConfigured("DJANGO_ENV deve ser development ou production.")
IS_PRODUCTION = ENVIRONMENT == "production"
if not IS_PRODUCTION:
    load_dotenv(BASE_DIR / ".env")


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Configure a variável {name} no ambiente ou .env.")
    return value


def csv_env(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def bool_env(name, default=False):
    value = os.environ.get(name, "").strip().lower() or str(default).lower()
    if value not in {"true", "false"}:
        raise ImproperlyConfigured(f"{name} deve ser true ou false.")
    return value == "true"


try:
    AUTH_TRUSTED_PROXY_IPS = {str(ip_address(value)) for value in csv_env("DJANGO_TRUSTED_PROXY_IPS")}
except ValueError as exc:
    raise ImproperlyConfigured("DJANGO_TRUSTED_PROXY_IPS deve conter apenas IPs explícitos separados por vírgula.") from exc


SECRET_KEY = required("DJANGO_SECRET_KEY")
DEBUG = bool_env("DJANGO_DEBUG")
ALLOWED_HOSTS = csv_env("DJANGO_ALLOWED_HOSTS", "" if IS_PRODUCTION else "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")
if IS_PRODUCTION:
    if DEBUG:
        raise ImproperlyConfigured("Produção não permite DJANGO_DEBUG=true.")
    if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
        raise ImproperlyConfigured("Produção exige DJANGO_SECRET_KEY aleatória, exclusiva e com pelo menos 50 caracteres.")
    if not ALLOWED_HOSTS or any("*" in host or host.startswith(".") for host in ALLOWED_HOSTS):
        raise ImproperlyConfigured("Produção exige DJANGO_ALLOWED_HOSTS com hosts explícitos, sem curingas.")
    if any(not origin.startswith("https://") or "*" in origin for origin in CSRF_TRUSTED_ORIGINS):
        raise ImproperlyConfigured("Produção aceita somente origens CSRF HTTPS explícitas.")
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "rest_framework",
    "apps.accounts", "apps.categories", "apps.transactions", "apps.reports",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if IS_PRODUCTION:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": required("POSTGRES_DB"), "USER": required("POSTGRES_USER"),
    "PASSWORD": required("POSTGRES_PASSWORD"),
    "HOST": required("POSTGRES_HOST"), "PORT": required("POSTGRES_PORT"),
    "OPTIONS": {"connect_timeout": 5},
}}
database_sslmode = os.environ.get("POSTGRES_SSLMODE", "").strip() or ("" if IS_PRODUCTION else "prefer")
if database_sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured("Configure POSTGRES_SSLMODE explicitamente em produção.")
DATABASES["default"]["OPTIONS"]["sslmode"] = database_sslmode
if os.environ.get("POSTGRES_SSLROOTCERT", "").strip():
    DATABASES["default"]["OPTIONS"]["sslrootcert"] = os.environ["POSTGRES_SSLROOTCERT"].strip()
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_RATES": {"login": "5/min", "register": "10/hour"},
}
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
if IS_PRODUCTION:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    WHITENOISE_ALLOW_ALL_ORIGINS = False
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
LOGIN_URL = "login"
CSRF_FAILURE_VIEW = "apps.accounts.views.csrf_failure"

# Only enable after the trusted proxy strips incoming X-Forwarded-Proto and
# supplies its own value, and direct access to the application is blocked.
SECURE_PROXY_SSL_HEADER = None
if IS_PRODUCTION and bool_env("DJANGO_TRUST_PROXY_HEADERS"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

try:
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "").strip() or "0") if IS_PRODUCTION else 0
except ValueError as exc:
    raise ImproperlyConfigured("DJANGO_HSTS_SECONDS deve ser um inteiro não negativo.") from exc
if SECURE_HSTS_SECONDS < 0:
    raise ImproperlyConfigured("DJANGO_HSTS_SECONDS deve ser um inteiro não negativo.")
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

if IS_PRODUCTION:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"safe": {"()": "config.logging.SafeProductionFormatter"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe"}},
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        },
    }
