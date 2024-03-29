
import environ

ROOT_DIR = (
    environ.Path(__file__) - 3
)  # (looking_for_group/config/settings/base.py - 3 = looking_for_group/)
APPS_DIR = ROOT_DIR.path("looking_for_group")

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path(".env")))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "America/New_York"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {"default": env.db("DATABASE_URL", default="postgis:///looking_for_group")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"

APPEND_SLASH = True

# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # Handy template tags
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.gis",
]

THIRD_PARTY_APPS = [
    "foundation_formtags",  # Form layouts
    "django_extensions",
    "cookielaw",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "rest_framework",
    "avatar",
    "django_registration",
    "pwned_passwords_django",
    "isbn_field",
    "taggit",
    "rules.apps.AutodiscoverRulesConfig",
    "star_ratings",
    "django_q",
    "schedule",
    "notifications",
    "haystack",
    "markdown_filter",
    "django_node_assets",
    "ajax_select",
    "postman",
    "markdownify",
    "keybase_proofs",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "allauth_2fa",
    "crispy_forms",
    "django_filters",
    "drf_yasg",
    "oauth2_provider",
    "corsheaders",
]
LOCAL_APPS = [
    "looking_for_group.users.apps.UsersConfig",
    "looking_for_group.game_catalog.apps.GameCatalogConfig",
    "looking_for_group.gamer_profiles.apps.GamerProfilesConfig",
    "looking_for_group.discord",
    "looking_for_group.games.apps.GamesConfig",
    "looking_for_group.user_preferences.apps.UserPreferencesConfig",
    "looking_for_group.invites.apps.InvitesConfig",
    "looking_for_group.motd.apps.MotdConfig",
    "looking_for_group.adminutils.apps.AdminutilsConfig",
    "looking_for_group.mailnotify.apps.MailnotifyConfig",
    "looking_for_group.rpgcollections.apps.RpgcollectionsConfig",
    "looking_for_group.tours.apps.ToursConfig",
    "looking_for_group.world.apps.WorldConfig",
    "looking_for_group.locations.apps.LocationsConfig",
    "looking_for_group.helpdesk.apps.HelpdeskConfig",
    "looking_for_group.releasenotes.apps.ReleasenotesConfig",
    # Your stuff: custom apps go here
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "looking_for_group.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "rules.permissions.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "oauth2_provider.backends.OAuth2Backend",
]

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
ACCOUNT_USERNAME_VALIDATORS = "looking_for_group.users.validators.custom_validators"
ACCOUNT_ADAPTER = "looking_for_group.users.adapters.AccountAdapter"
ACCOUNT_FORMS = {"signup": "looking_for_group.users.forms.LFGSignupForm"}
SOCIALACCOUNT_ADAPTER = "looking_for_group.users.adapters.SocialAccountAdapter"
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "/dashboard/"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# REST FRAMEWORK
# ------------------------------------------------------------------------------
#
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}
OAUTH2_PROVIDER = {"SCOPES": {"full": "Access to read and write data in your account."}}
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        # "basic": {
        #     "type": "basic",
        #     "description": "When using the API from within the same domain using the JavaScript API, it can use the existing session.",
        # },
        "oauth2": {
            "type": "oauth2",
            "description": "Any external application needs to register their application with us and use OAuth for authentication.",
            "flow": "accessCode",
            "authorizationUrl": "https://app.lfg.directory/o/authorize/",
            "tokenUrl": "https://app.lfg.directory/o/token/",
            "scopes": OAUTH2_PROVIDER["SCOPES"],
        }
    }
}

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "pwned_passwords_django.validators.PwnedPasswordsValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.forwarded_host.SetRemoteAddrFromForwardedFor",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "allauth_2fa.middleware.AllauthTwoFactorMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "looking_for_group.users.middleware.TimezoneSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR.path("staticfiles"))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/staticfiles/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR.path("static"))]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR.path("media"))
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        "NAME": "default",
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR.path("templates"))],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            "debug": DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "looking_for_group.motd.context_processors.motd",
                "looking_for_group.context_processors.app_version",
                "looking_for_group.context_processors.has_two_factor",
                "looking_for_group.tours.context_processors.completed_tours",
                "postman.context_processors.inbox",
            ],
        },
    },
    {
        "NAME": "light",
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR.path("user_preferences").path("templates"))],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            "debug": DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": ["django.template.loaders.filesystem.Loader"],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                # "django.template.context_processors.debug",
                # "django.template.context_processors.request",
                # "django.contrib.auth.context_processors.auth",
                # "django.template.context_processors.i18n",
                # "django.template.context_processors.media",
                # "django.template.context_processors.static",
                # "django.template.context_processors.tz",
            ],
        },
    },
]

# Workaround for drf_yasg, which expects to find the django template engine with the key "django" instead of "default"
django_template = TEMPLATES[0].copy()
django_template["NAME"] = "django"
TEMPLATES.append(django_template)

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Daniel Andrlik""", "daniel@andrlik.org")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS


# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "looking_for_group.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "looking_for_group.users.adapters.SocialAccountAdapter"
# SOCIALACCOUNT_PROVIDERS = {
#     "discord_with_guilds": {
#         'SCOPE': ['email', 'identify', 'guilds'],
#     },
# }
SOCIALACCOUNT_EMAIL_VERIFICATION = False
# Custom user app defaults
# Select the correct user model
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "users:redirect"
LOGIN_URL = "account_login"

# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = "slugify.slugify"


# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/quickstart/#installation
INSTALLED_APPS += ["compressor"]
STATICFILES_FINDERS += [
    "compressor.finders.CompressorFinder",
    "django_node_assets.finders.NodeModulesFinder",
]
NODE_PACKAGE_JSON = str(ROOT_DIR("package.json"))
NODE_MODULES_ROOT = str(ROOT_DIR("node_modules"))
COMPRESS_ENABLED = True

# django-libsass
COMPRESS_PRECOMPILERS = [("text/x-scss", "django_libsass.SassCompiler")]

COMPRESS_CACHEABLE_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
LIBSASS_SOURCEMAPS = True

# Minification
# if not DEBUG:
COMPRESS_FILTERS = {
    "css": [
        "compressor.filters.css_default.CssAbsoluteFilter",
        "compressor.filters.cssmin.rCSSMinFilter",
    ],
    "js": ["compressor.filters.jsmin.JSMinFilter"],
}

# Your stuff...
# ------------------------------------------------------------------------------
# Avatar settings
# ------------------------------------------------------------------------------
AVATAR_EXPOSE_USERNAMES = False
AVATAR_GRAVATAR_DEFAULT = "identicon"
AVATAR_CLEANUP_DELETED = True
AVATAR_AUTO_GENERATE_SIZES = (80, 30)
AVATAR_GRAVATAR_BASE_URL = "https://www.gravatar.com/avatar/"
AVATAR_GRAVATAR_FIELD = "avatar_email"


# -----------------------------------------------------------------------------
# Star Ratings
# -----------------------------------------------------------------------------
STAR_RATINGS_RATING_MODEL = "gamer_profiles.MyRating"
STAR_RATINGS_OBJECT_ID_PATTERN = (
    "[0-9A-F]{8}-[0-9A-F]{4}-[4][0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}"
)

# ------------------------------------------------------------------------------
# Django Q
# ------------------------------------------------------------------------------

Q_CLUSTER = {"name": "looking_for_group"}

# ------------------------------------------------------------------------------
# Notifications
# ------------------------------------------------------------------------------

DJANGO_NOTIFICATIONS_CONFIG = {"USE_JSONFIELD": True}

MARKDOWN_FILTER_WHITELIST_TAGS = ["a", "p", "code", "h1"]

# ------------------------------------------------------------------------------
# Postman
# ------------------------------------------------------------------------------

POSTMAN_I18N_URLS = True
POSTMAN_DISALLOW_ANONYMOUS = True
POSTMAN_NOTIFIER_APP = "looking_for_group.mailnotify"
POSTMAN_DISABLE_USER_EMAILING = True
POSTMAN_AUTO_MODERATE_AS = True
POSTMAN_AUTOCOMPLETER_APP = {
    "name": "ajax_select",
    "field": "AutoCompleteField",
    "arg_name": "channel",
    "arg_default": "gamers",
}
AJAX_SELECT_BOOTSTRAP = False
MARKDOWNIFY_FILTER_WHITELIST_TAGS = [
    "a",
    "abbr",
    "code",
    "acronym",
    "b",
    "blockquote",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "ul",
]
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")
# ----------------------------------------------------------------------------
# HelpDesk Credentials
# ----------------------------------------------------------------------------

GITLAB_URL = env("GITLAB_URL", default="https://gitlab.com")
GITLAB_TOKEN = env("GITLAB_TOKEN", default=None)
GITLAB_PROJECT_ID = env("GITLAB_PROJECT_ID", default=None)
GITLAB_DEFAULT_USERNAME = env("GITLAB_DEFAULT_USERNAME", default="daniel")
GITLAB_DEFAULT_REMOTE_USERNAME = env(
    "GITLAB_DEFAULT_REMOTE_USERNAME", default="andrlik"
)
KEYBASE_PROOFS_DOMAIN = "app.lfg.directory"
RELEASE_NOTES_FILENAME = "CHANGELOG.rst"

# ----------------------------------------------------------------------------
# CORS Settings
# ----------------------------------------------------------------------------

CORS_ORIGIN_ALLOW_ALL = True
CORS_URLS_REGEX = r"^/api/.*$"
