from django.apps import AppConfig


class HelpdeskConfig(AppConfig):
    name = "looking_for_group.helpdesk"
    verbose_name = "Help Desk"

    def ready(self):
        from . import receivers  # noqa
