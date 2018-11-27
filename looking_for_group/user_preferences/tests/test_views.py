import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db import InterfaceError
from psycopg2 import InterfaceError as PGInterfaceError
from schedule.models import Calendar
from test_plus import TestCase

from ...gamer_profiles import models as social_models
from ...games.models import GamePosting
from ...games.tests.test_views import AbstractGameSessionTest
from ...users.models import User
from ..models import Preferences


class SettingsViewTest(TestCase):
    """
    Test settings view and editing.
    """
    def setUp(self):
        self.user = self.make_user(username='booga')
        self.gamer = self.user.gamerprofile

    def test_login_required(self):
        assert Preferences.objects.get(gamer=self.gamer)
        self.assertLoginRequired('user_preferences:setting-view')
        self.assertLoginRequired('user_preferences:setting-edit')

    def test_view_load(self):
        with self.login(username=self.gamer.username):
            self.assertGoodView('user_preferences:setting-view')
            self.assertGoodView('user_preferences:setting-edit')

    def test_update_settings(self):
        self.post_data = {
            'news_emails': '1',
            'notification_digest': '1',
            'feedback_volunteer': '1',
        }
        with self.login(username=self.gamer.username):
            self.post('user_preferences:setting-edit', data=self.post_data)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            new_version = Preferences.objects.get(gamer=self.gamer)
            assert new_version.news_emails and new_version.notification_digest and new_version.feedback_volunteer


class DashboardTest(AbstractGameSessionTest):
    """
    Test the dashboard.
    """
    def setUp(self):
        super().setUp()
        self.view_name = 'dashboard'

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_page_load(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name)


class DeleteAccountTest(AbstractGameSessionTest):
    """
    Test deleting a user using an async task. Ensure all connected
    data items are removed.
    """
    def setUp(self):
        super().setUp()
        self.view_name = "user_preferences:account_delete"

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_load_correct(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name)

    def test_post_without_confirm(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data={})
            self.response_200()
            assert social_models.GamerProfile.objects.get(pk=self.gamer1.pk)

    # def test_with_correct_confirm(self):
    #     with self.login(username=self.gamer1.username):
    #         self.get(self.view_name)
    #         delete_key = self.get_context('delete_confirm_key')
    #         try:
    #             self.post(self.view_name, data={'delete_confirm_key': delete_key})
    #         except InterfaceError:
    #             print("Typical error occurred, moving foward with checks")
    #         except PGInterfaceError:
    #             print("typical async error occurred")
    #         self.response_302()
    #         with pytest.raises(ObjectDoesNotExist):
    #             User.objects.get(id=self.gamer1.user.id)
    #         with pytest.raises(ObjectDoesNotExist):
    #             social_models.GamerProfile.objects.get(pk=self.gamer1.pk)
    #         with pytest.raises(ObjectDoesNotExist):
    #             GamePosting.objects.get(pk=self.gp2.id)
    #         with pytest.raises(ObjectDoesNotExist):
    #             Calendar.objects.get(slug=self.gamer1.username)
