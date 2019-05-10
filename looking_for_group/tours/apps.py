from django.apps import AppConfig


class ToursConfig(AppConfig):
    name = 'looking_for_group.tours'
    verbose_name = "Tours"

    def ready(self):
        from . import receivers  # noqa
