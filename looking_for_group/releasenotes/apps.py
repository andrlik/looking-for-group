from django.apps import AppConfig


class ReleasenotesConfig(AppConfig):
    name = "looking_for_group.releasenotes"
    verbose_name = "Release Notes"

    def ready(self):
        from . import receivers  # noqa
