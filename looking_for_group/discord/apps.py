from django.apps import AppConfig


class DiscordConfig(AppConfig):
    name = "looking_for_group.discord"
    verbose_name = "Discord"

    def ready(self):  # pragma: no cover
        from . import receivers  # noqa: F401
