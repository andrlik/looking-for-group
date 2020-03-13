import os
from urllib.parse import urlparse

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

import looking_for_group

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["geek-looking-for-group.herokuapp.com"]
)

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"] = env.db("DATABASE_URL")  # noqa F405
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # noqa F405
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa F405

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDISCLOUD_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}
# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^health/"]
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = False
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# STORAGES
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/#installation
INSTALLED_APPS += ["storages"]  # noqa F405
AWS_REGION_NAME = env("DJANGO_AWS_REGION_NAME", default="us-east-1")
AWS_IS_GZIPPED = env.bool("DJANGO_AWS_IS_GZIPPED", default=True)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID")
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY")
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_STORAGE_BUCKET_NAME = env("DJANGO_AWS_STORAGE_BUCKET_NAME")
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_AUTO_CREATE_BUCKET = True
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_QUERYSTRING_AUTH = False
# DO NOT change these unless you know what you're doing.
_AWS_EXPIRY = 60 * 60 * 24 * 7
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": f"max-age={_AWS_EXPIRY}, s-maxage={_AWS_EXPIRY}, must-revalidate"
}

# STATIC
# ------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# MEDIA
# ------------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
MEDIA_URL = "https://s3.amazonaws.com/{AWS_STORAGE_BUCKET_NAME}/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa F405
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default="Looking for Group <noreply@mg.lfg.directory>"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default="[Looking for Group]")


# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# Anymail (Mailgun)
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]  # noqa F405
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN"),
}

# Gunicorn
# ------------------------------------------------------------------------------
# INSTALLED_APPS += ['gunicorn']  # noqa F405
# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#enable-whitenoise
MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa F405
# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_ENABLED
COMPRESS_ENABLED = env.bool("COMPRESS_ENABLED", default=True)
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_STORAGE
COMPRESS_STORAGE = "compressor.storage.CompressorFileStorage"
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_URL
COMPRESS_URL = STATIC_URL  # noqa F405
COMPRESS_OFFLINE = env.bool("COMPRESS_OFFLINE", default=True)
# ------------------------------------------------------------------------------
# https://docs.sentry.io/clients/python/integrations/django/

MIDDLEWARE = ["allow_cidr.middleware.AllowCIDRMiddleware"] + MIDDLEWARE  # noqa: F405
ALLOWED_CIDR_NETS = env.list(
    "DJANGO_ALLOWED_CIDR_NETS", default=["12.0.0.0/11", "10.0.0.0/16", "172.31.0.0/11"]
)
# Sentry
# ------------------------------------------------------------------------------
SENTRY_DSN = env("DJANGO_SENTRY_DSN")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "root": {"level": "WARNING", "handlers": ["console"]},
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "sentry.errors": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "gamer_profiles": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "games": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "rules": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "discord": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "helpdesk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "locations": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "api": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "releasenotes": {"level": "ERROR", "handlers": ["console"], "propagate": False},
    },
}


# SENTRY_CELERY_LOGLEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    release=looking_for_group.__version__,
)

# Your stuff...
# ------------------------------------------------------------------------------
Q_CLUSTER["django_redis"] = "default"  # noqa:F405

# Haystack

GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")
GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")

es = urlparse(os.environ.get("SEARCHBOX_SSL_URL", "http://127.0.0.1:9200/"))

es_port = es.port or 80

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.elasticsearch5_backend.Elasticsearch5SearchEngine",
        "URL": os.environ.get("SEARCHBOX_SSL_URL"),
        "INDEX_NAME": "documents",
    }
}

if es.username:
    HAYSTACK_CONNECTIONS["default"]["KWARGS"] = {
        "http_auth": es.username + ":" + es.password
    }

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [  # noqa: F405
    "rest_framework.throttling.AnonRateThrottle",
    "rest_framework.throttling.UserRateThrottle",
]

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "15/minute",
    "user": "60/minute",
}
