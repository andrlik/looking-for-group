import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

from ...game_catalog.tests.test_accessibility import BaseAccessibilityTest
from ..tests.test_views import AbstractUtilsTest


@pytest.mark.accessibility
@pytest.mark.nondestructive
class AdminUtilsAccessibilityTest(BaseAccessibilityTest, AbstractUtilsTest, StaticLiveServerTestCase):
    """
    Run accessibility tests on admin util views.
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.admin_gamer.user.username
        self.login_browser()

    def test_notification_view(self):
        axe, violations = self.get_axe_violations(reverse("adminutils:notification"))
        assert len(violations) == 0, axe.report(violations)

    def test_email_view(self):
        axe, violations = self.get_axe_violations(reverse("adminutils:email"))
        assert len(violations) == 0, axe.report(violations)
