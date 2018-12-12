from django.contrib.sites.models import Site
from notifications.models import Notification

from ...users.models import User
from ..tasks import send_mass_email, send_mass_notifcation
from .test_views import AbstractUtilsTest


class NotificationTest(AbstractUtilsTest):
    """
    Test generating a bunch of notifications.
    """

    def test_notification_send(self):
        prior_notifications = Notification.objects.count()
        site = Site.objects.all()[0]
        send_mass_notifcation(site, "You look tired, friend.", User.objects.all())
        assert Notification.objects.count() == User.objects.count() + prior_notifications


class EmailTest(AbstractUtilsTest):
    """
    Test for sending a mass email.
    """

    def test_email_send(self):
        subject = "this is a test email"
        body = """We're gonna **do** this!"""
        send_mass_email(subject, body, User.objects.all())
