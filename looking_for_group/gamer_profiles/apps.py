from django.apps import AppConfig


class GamerProfilesConfig(AppConfig):
    name = "gamer_profiles"
    verbose_name = "Gamer Profiles"

    def ready(self):  # pragma: no cover
        from . import receivers  # noqa: F401
