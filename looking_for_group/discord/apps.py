import logging
from django.apps import AppConfig

logger = logging.getLogger('discord')


class DiscordConfig(AppConfig):
    name = 'looking_for_group.discord'
    verbose_name = 'Discord'

    def ready(self):  # pragma: no cover
        from . import receivers  # noqa: F401
        logger.debug("Successfully loaded receivers")
