import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

from ...game_catalog.tests.test_accessibility import BaseAccessibilityTest
from ...games.tests.test_views import AbstractGameSessionTest


@pytest.mark.accessibility
@pytest.mark.nondestructive
class UserPreferencesViewTest(BaseAccessibilityTest, AbstractGameSessionTest, StaticLiveServerTestCase):
    """
    Test all the user preferences views for accessibility
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.gamer1.user.username
        self.login_browser()

    def test_setting_view(self):
        axe, violations = self.get_axe_violations(reverse("user_preferences:setting-view"))
        assert len(violations) == 0, axe.report(violations)

    def test_setting_edit_view(self):
        axe, violations = self.get_axe_violations(reverse("user_preferences:setting-edit"))
        assert len(violations) == 0, axe.report(violations)

    def test_dashboard(self):
        axe, violations = self.get_axe_violations(reverse("dashboard"))
        assert len(violations) == 0, axe.report(violations)
