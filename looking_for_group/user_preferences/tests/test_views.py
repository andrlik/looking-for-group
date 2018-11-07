from test_plus import TestCase

from ...games.tests.test_views import AbstractGameSessionTest
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
