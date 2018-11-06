from django.apps import AppConfig


class UserPreferencesConfig(AppConfig):
    name = 'looking_for_group.user_preferences'
    verbose_name = "User Preferences"

    def ready(self):  # pragma: no cover
        from . import receivers  # noqa: F401
