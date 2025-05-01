import tempfile
from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
import sys

env = environ.Env(overwrite=True)
root_path = environ.Path(__file__) - 2
env.read_env(str(root_path.path(".env")))
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_ROOT      = BASE_DIR / "uploads"                 # production / canonical
LOCAL_MEDIA_ROOT  = BASE_DIR / "local_media" / "uploads"
from kombu import Queue


# -----------------------------------------------------------------------------
# Basic Config
# -----------------------------------------------------------------------------
ROOT_URLCONF = "conf.urls"
WSGI_APPLICATION = "conf.wsgi.application"
DEBUG = env.bool("DEBUG", default=True)
REMOTE_STATIC_FILES = env.bool("REMOTE_STATIC_FILES", default=True)


# -----------------------------------------------------------------------------
# Time & Language
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Security and Users
# -----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = ["https://artfairai.com", "https://dev.artfairai.com", "https://www.artfairai.com", "http://127.0.0.1", "http://localhost", 'http://dev.artfairai.com', 'http://www.dev.artfairai.com', 'https://www.staging.artfairai.com', 'https://staging.artfairai.com']
AUTH_USER_MODEL = "users.CustomUser"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -----------------------------------------------------------------------------
# Databases
# -----------------------------------------------------------------------------
# DJANGO_DATABASE_URL = env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
# DATABASES = {'default': DJANGO_DATABASE_URL}
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / "db.sqlite3",
#     }
# }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="postgres"),
        "USER": env("DB_USER", default="artfair_dev_user"),
        "PASSWORD": env("DB_PASSWORD", default="artfairdev!Password"),
        "HOST": env("DB_HOST", default="artfair-devDB.c7aei6sm4zqz.us-east-1.rds.amazonaws.com"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------------
# Applications configuration
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # 3rd party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'dj_rest_auth',
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'allauth.socialaccount.providers.google',
    # 'rest_framework_swagger',
    "corsheaders",
    "rest_framework",
    "django_filters",
    "knox",
    "django_celery_beat",
    "django_celery_results",
    "drf_spectacular",
    # local apps
    "apps.analytics",
    "apps.users",
    "apps.core",
    "apps.training_data",
    "apps.licensing",
    "apps.billing",
    # django storage
    "storages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [root_path("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# -----------------------------------------------------------------------------
# Rest Framework
# -----------------------------------------------------------------------------
REST_KNOX = {
    "SECURE_HASH_ALGORITHM": "hashlib.sha512",
    "AUTH_TOKEN_CHARACTER_LENGTH": 64,
    "TOKEN_TTL": timedelta(hours=10),
    "USER_SERIALIZER": "apps.users.serializers.UserProfileSerializer",
    "TOKEN_LIMIT_PER_USER": None,
    "AUTO_REFRESH": False,
    "AUTO_REFRESH_MAX_TTL": None,
    "MIN_REFRESH_INTERVAL": 60,
    "AUTH_HEADER_PREFIX": "Bearer",
    "TOKEN_MODEL": "knox.AuthToken",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("knox.auth.TokenAuthentication",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# TODO ⚡ Update the settings for the DRF Spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "Django Starter Template",
    "DESCRIPTION": "A comprehensive starting point for your new API with Django and DRF",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [
        {"BearerAuth": []}  # Reference the BearerAuth scheme
    ],
    "AUTHENTICATION_WHITELIST": ["knox.auth.TokenAuthentication"],
    "SCHEMA_AUTHENTICATION_CLASSES": [
        "knox.auth.TokenAuthentication",
    ],
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] += (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    )

    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
        "rest_framework.renderers.BrowsableAPIRenderer",
    )

CORS_ALLOW_ALL_ORIGINS = DEBUG

if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

USER_AGENTS_CACHE = "default"


# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
# CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Santiago"
CELERY_RESULT_EXTENDED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_QUEUES = (
    Queue("default", routing_key="default"),
    Queue("video_processing", routing_key="video_processing"),
    Queue("caption_processing",routing_key="caption_processing"),
    Queue("download_file_s3",routing_key="downloading_processing"),
)


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")


# -----------------------------------------------------------------------------
# Error Reporting via Email (Built‑in)
# -----------------------------------------------------------------------------
# ADMINS will receive an email whenever a 500 error occurs.
ADMINS = [
    ("Site Admin", "christopher.campbell.t@gmail.com"),
]

# MANAGERS can also be defined (often same as ADMINS)
MANAGERS = ADMINS


# -----------------------------------------------------------------------------
# Sentry and logging
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "dev_mail_admins": {
            "level": "ERROR",
            "class": "conf.handlers.ForceAdminEmailHandler",
            # "formatter": "console",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "file",
            "filename": f"{root_path('logs')}/error.log",
            "maxBytes": 1000000,
            "backupCount": 20,
        },
    },
    "formatters": {
        "console": {
            "format": "%(name)-12s %(levelname)-8s %(message)s"
        },
        "file": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "file", "dev_mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}



if not DEBUG:
    sentry_sdk.init(
        dsn=env("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
        send_default_pii=True,
    )

# -----------------------------------------------------------------------------
# S3 Settings
# -----------------------------------------------------------------------------

TESTING = ((" ".join(sys.argv)).find('manage.py test') != -1)
if TESTING:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

if REMOTE_STATIC_FILES:
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default='artfair-development')
    AWS_S3_REGION = env("AWS_S3_REGION", default='us-east-1')
    # AWS_PROFILE_NAME = env("AWS_PROFILE_NAME", default='ElevatedDeploymentProvisioner')

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION,
                # "profile_name": AWS_PROFILE_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION,
                # "profile_name": AWS_PROFILE_NAME,
                "location": "static"  # This puts static files in a 'static' directory in your bucket
            },
        },
    }

    # Update static URL to point to S3
    STATIC_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/static/'

    AWS_S3_FILE_OVERWRITE = False  # Don't overwrite files with the same name
    # AWS_DEFAULT_ACL = 'public-read'  # Make files publicly readable
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # Cache files for 24 hours
    }

    MEDIA_ROOT = root_path("media_root")
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/media/'


else:
    # -----------------------------------------------------------------------------
    # Static & Media Files
    # -----------------------------------------------------------------------------

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    STATIC_URL = "/static/"
    STATICFILES_DIRS = [root_path("static")]

    if DEBUG:
        STATIC_ROOT = tempfile.mkdtemp()
    else:
        STATIC_ROOT = root_path("static_root")

    # MEDIA_ROOT = root_path("media_root")
    # MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/media/'
    MEDIA_URL = "/media/"

ADMIN_MEDIA_PREFIX = STATIC_URL + "admin/"


# -----------------------------------------------------------------------------
# Django Debug Toolbar and Django Extensions
# -----------------------------------------------------------------------------
# if DEBUG:
#     INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
#     INTERNAL_IPS = ["127.0.0.1"]
#     MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
#

AUTH_USER_MODEL = 'users.CustomUser'

worker_max_memory_per_child = 500000  # 500 MB per worker



# -----------------------------------------------------------------------------
# Django Allauth and Social Account
# -----------------------------------------------------------------------------

SITE_ID = 1
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'optional'

SOCIALACCOUNT_PROVIDERS = {
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name'],
        'VERSION': 'v16.0',  # Use the latest Facebook API version
    },
    'google': {
            'SCOPE': [
                'profile',
                'email',
            ],
            'AUTH_PARAMS': {
                'access_type': 'offline',
            },
            'METHOD': 'oauth2',  # Use OAuth2
            'USER_INFO_URL': 'https://www.googleapis.com/oauth2/v3/userinfo',  # Default user info endpoint
        }
}


# -----------------------------------------------------------------------------
#  Password Reset Settings
# -----------------------------------------------------------------------------

PASSWORD_RESET_TIMEOUT = 900
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False

FRONTEND_RESET_PASSWORD_URL = env("FRONTEND_RESET_PASSWORD_URL", default="http://localhost:3000/reset-password")



HF_TOKEN = env("HF_TOKEN", default="")
