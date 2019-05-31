import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

from looking_for_group.game_catalog.tests.test_accessibility import BaseAccessibilityTest
from looking_for_group.rpgcollections.tests.test_views import AbstractCollectionsTest


@pytest.mark.accessibility
@pytest.mark.nondestructive
class TestRPGViews(BaseAccessibilityTest, AbstractCollectionsTest, StaticLiveServerTestCase):
    """
    Test collection views for accessibility.
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.gamer1.user.username
        self.login_browser()

    def test_detail_view(self):
        axe, violations = self.get_axe_violations(reverse("rpgcollections:book-detail", kwargs={"book": self.cypher_collect_1.slug}))
        assert len(violations) == 0, axe.report(violations)

    def test_edit_view(self):
        axe, violations = self.get_axe_violations(reverse("rpgcollections:edit-book", kwargs={"book": self.cypher_collect_1.slug}))
        assert len(violations) == 0, axe.report(violations)

    def test_delete_view(self):
        axe, violations = self.get_axe_violations(reverse("rpgcollections:remove-book", kwargs={"book": self.cypher_collect_1.slug}))
        assert len(violations) == 0, axe.report(violations)
