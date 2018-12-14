from django.apps import AppConfig


class MailnotifyConfig(AppConfig):
    name = 'looking_for_group.mailnotify'

    def ready(self):
        from . import receivers  # noqa
