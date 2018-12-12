from ...gamer_profiles.models import GamerProfile
from ...gamer_profiles.tests import factories
from ...games.tests.test_views import AbstractViewTestCaseSignals
from ...user_preferences.models import Preferences
from ...users.models import User
from ..views import get_filtered_user_queryset


class AbstractUtilsTest(AbstractViewTestCaseSignals):

    def setUp(self):
        super().setUp()
        self.admin_gamer = factories.GamerProfileFactory()
        self.admin_gamer.user.is_superuser = True
        self.admin_gamer.user.save()
        Preferences.objects.create(gamer=self.gamer1, notification_digest=True)
        Preferences.objects.create(gamer=self.gamer2, feedback_volunteer=True)
        for gamer in GamerProfile.objects.exclude(id__in=[self.gamer1.pk, self.gamer2.pk]):
            Preferences.objects.create(gamer=gamer)


class FilterTest(AbstractUtilsTest):

    def setUp(self):
        super().setUp()

    def test_filtering_empty(self):
        assert get_filtered_user_queryset([], 'any').count() == User.objects.count()

    def test_filtering_any(self):
        assert get_filtered_user_queryset(['notification_digest', 'feedback_volunteer'], "any").count() == 2

    def test_filtering_all(self):
        assert get_filtered_user_queryset(['notification_digest', 'feedback_volunteer'], "all").count() == 0

    def test_filtering_none(self):
        assert get_filtered_user_queryset(['notification_digest', 'feedback_volunteer'], "none").count() == User.objects.count() - 2


class TestNotificationSend(AbstractUtilsTest):

    def setUp(self):
        super().setUp()
        self.view_name = 'adminutils:notification'

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name)
            self.response_403()

    def test_admin_access(self):
        with self.login(username=self.admin_gamer.username):
            self.assertGoodView(self.view_name)

    def test_post_notification(self):
        with self.login(username=self.admin_gamer.username):
            self.post(self.view_name, data={'message': "Hello, friend", 'filter_options': ['feedback_volunteer'], 'filter_mode': 'any'})
            self.response_302()


class TestEmailSend(AbstractUtilsTest):

    def setUp(self):
        super().setUp()
        self.view_name = 'adminutils:email'

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name)
            self.response_403()

    def test_admin_access(self):
        with self.login(username=self.admin_gamer.username):
            self.assertGoodView(self.view_name)

    def test_mass_email(self):
        with self.login(username=self.admin_gamer.username):
            self.post(self.view_name, data={"subject": "Greetings", "body": "Do you have the time?", "filter_options": ["feedback_volunteer"], "filter_mode": "any"})
            self.response_302()
