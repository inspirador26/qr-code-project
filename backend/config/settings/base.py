"""
Shared settings for all environments. Environment-specific settings
(dev.py, prod.py) import from here and override as needed.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Custom user model must be set before the first migration.
AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "oauth2_provider",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    # Local apps
    "tenancy",
    "accounts",
    "offers",
    "coupons",
    "tcb_integration",
    "gs1",
    "wallet",
    "reporting",
    "api",
    "internal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Resolves the acting tenant for the request; see tenancy/middleware.py.
    "tenancy.middleware.TenantContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

DATABASES = {
    "default": env.db(
        # Port 5433, not 5432 — see docker-compose.yml: this machine already
        # runs a native Postgres service on 5432.
        "DATABASE_URL",
        default="postgres://coupon_platform:coupon_platform@localhost:5433/coupon_platform",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# django-oauth-toolkit's migrations resolve this via django's swappable-model
# machinery even when using its default Application model — must be set
# explicitly or `makemigrations`/`migrate` fail trying to resolve it.
OAUTH2_PROVIDER_APPLICATION_MODEL = "oauth2_provider.Application"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Third-party app config -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# django-allauth: SSO only, no local username/password signup — CPG users
# are provisioned via invite (see accounts app), not self-service signup.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_EMAIL_VERIFICATION = "none"  # identity is asserted by the SSO provider
SOCIALACCOUNT_AUTO_SIGNUP = False  # enforced by our own invite-matching adapter
SOCIALACCOUNT_ADAPTER = "accounts.adapters.InviteOnlySocialAccountAdapter"
LOGIN_REDIRECT_URL = "/"

# --- TCB integration (platform-level credentials, not per-tenant) ----------
# See backend/tcb_integration/ — one credential pair per TCB role.

TCB_API_BASE_URL = env("TCB_API_BASE_URL", default="https://api.portal.thecouponbureau.org")
TCB_AUTHORIZED_PARTNER_ACCESS_KEY = env("TCB_AUTHORIZED_PARTNER_ACCESS_KEY", default="")
TCB_AUTHORIZED_PARTNER_SECRET_KEY = env("TCB_AUTHORIZED_PARTNER_SECRET_KEY", default="")
TCB_PROVIDER_ACCESS_KEY = env("TCB_PROVIDER_ACCESS_KEY", default="")
TCB_PROVIDER_SECRET_KEY = env("TCB_PROVIDER_SECRET_KEY", default="")
# Our own email_domain as registered with TCB (identifies us as a Provider
# when assign_provider/deposit checks authorization) — see the plan's TCB
# integration seam section on TCB's email_domain-based identity model.
TCB_PLATFORM_EMAIL_DOMAIN = env("TCB_PLATFORM_EMAIL_DOMAIN", default="example.com")
# True until we have real TCB Authorized Partner + Provider credentials
# (plan Open Item 1) — every call goes to tcb_integration.mock_client
# instead of the real API. Flip to False (or unset, once real credentials
# are the norm) once TCB has provisioned our account. See
# tcb_integration/client.py's get_tcb_client().
TCB_USE_MOCK = env.bool("TCB_USE_MOCK", default=True)

# --- Google Wallet (platform-level Issuer, not per-tenant — see wallet/service.py) ---
# Ported from server.js's hardcoded ISSUER_ID/ISSUER_NAME/keys/wallet-sa.json.

GOOGLE_WALLET_ISSUER_ID = env("GOOGLE_WALLET_ISSUER_ID", default="")
GOOGLE_WALLET_ISSUER_NAME = env("GOOGLE_WALLET_ISSUER_NAME", default="")
GOOGLE_WALLET_SERVICE_ACCOUNT_FILE = env("GOOGLE_WALLET_SERVICE_ACCOUNT_FILE", default="")

# --- Celery ------------------------------------------------------------------
# Outbox worker for the TCB integration seam (deposit batches, audit polling).
# See Open Item 11 in the plan: swap to a DB-polled management command here
# if Redis is unwelcome infra for the MVP — CELERY_TASK_ALWAYS_EAGER=True
# below runs tasks synchronously with no broker as an interim option.

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
