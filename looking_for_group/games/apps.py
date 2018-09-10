from django.apps import AppConfig


class GamesConfig(AppConfig):
    name = "games"
    verbose_name = "Games"

    def ready(self):
        from . import receivers  # noqa
