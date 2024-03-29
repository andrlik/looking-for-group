from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="dDAgMGSsmkiqkQyCYFVdmK0WaweTbWLnUNBwTjF3MsQbEXPswmY8mQ0gcSv2llld",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "testserver"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        "LOCATION": "",
    }
}

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG  # noqa F405

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "localhost"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]


# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
# INSTALLED_APPS += ['django_extensions']  # noqa F405

# Your stuff...
# ------------------------------------------------------------------------------
# Django Q
# ------------------------------------------------------------------------------
Q_CLUSTER["orm"] = "default"  # noqa: F405

# ------------------------------------------------------------------------------
# Haystack
# ------------------------------------------------------------------------------

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.elasticsearch5_backend.Elasticsearch5SearchEngine",
        "URL": "http://127.0.0.1:9200/",
        "INDEX_NAME": "haystack",
    }
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
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
            "propagate": True,
        },
        "catalog": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "gamer_profiles": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "rules": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "discord": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "games": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "haystack": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "postman": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "tours": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "locations": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "helpdesk": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "api": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
        "releasenotes": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
    },
}

GITLAB_PROJECT_ID = env("GITLAB_TEST_PROJECT_ID", default=None)
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [  # noqa: F405
    "rest_framework.throttling.AnonRateThrottle",
    "rest_framework.throttling.UserRateThrottle",
]

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "15/minute",
    "user": "60/minute",
}
