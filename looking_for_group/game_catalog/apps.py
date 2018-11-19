from django.apps import AppConfig  # pragma: no cover


class GameCatalogConfig(AppConfig):  # pragma: no cover
    name = 'looking_for_group.game_catalog'  # pragma: no cover
    verbose_name = 'Game Catalog'

    def ready(self):
        from . import receivers # noqa
