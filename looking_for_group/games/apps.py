from django.apps import AppConfig


class GamesConfig(AppConfig):
    name = "looking_for_group.games"
    verbose_name = "Games"

    def ready(self):
        from . import receivers  # noqa
