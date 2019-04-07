from django.apps import AppConfig


class RpgcollectionsConfig(AppConfig):
    name = "looking_for_group.rpgcollections"
    verbose_name = "RPG Collections"

    def ready(self):
        from . import receivers  # noqa
