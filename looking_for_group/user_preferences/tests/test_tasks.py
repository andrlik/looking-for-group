from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification
from notifications.signals import notify

from .. import tasks
from ...games.tests.test_views import AbstractViewTestCaseSignals
from ..models import Preferences


class TestComponents(AbstractViewTestCaseSignals):

    def setUp(self):
        super().setUp()
        ContentType.objects.clear_cache()
        Preferences.objects.create(gamer=self.gamer1)
        Preferences.objects.create(gamer=self.gamer2)
        Preferences.objects.create(gamer=self.gamer3)
        notify.send(self.gamer2, recipient=self.gamer1.user, verb="sent you a friend request.")
        notify.send(self.gamer2, recipient=self.gamer1.user, verb="banned community user", action_object=self.gamer3, target=self.comm1)
        notify.send(self.gamer1, recipient=self.gamer3.user, verb="sent you a friend request.")
        notify.send(self.gamer3, recipient=self.gamer2.user, verb="sent you a friend request.")
        self.gamer1.preferences.notification_digest = True
        self.gamer1.preferences.save()
        self.gamer3.preferences.notification_digest = True
        self.gamer3.preferences.save()

    def tearDown(self):
        ContentType.objects.clear_cache()
        super().tearDown()

    def test_collect_users(self):
        user_list = tasks.get_users_with_digests()
        assert len(user_list) == 2

    def test_generate_single_email_body(self):
        user = self.gamer1.user
        notifications = Notification.objects.filter(recipient=user, unread=True, emailed=False)
        assert notifications.count() == 2
        txt_body, html_body = tasks.form_email_body(user, notifications)

    def test_email_sending(self):
        user = self.gamer1.user
        notifications = Notification.objects.filter(recipient=user, unread=True, emailed=False)
        tasks.send_digest_email(user, notifications)

    def test_full_process(self):
        tasks.perform_daily_digests()
