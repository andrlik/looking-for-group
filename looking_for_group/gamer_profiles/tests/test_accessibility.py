import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

from ...game_catalog.tests.test_accessibility import BaseAccessibilityTest
from ..tests.test_views import BaseAbstractViewTest


@pytest.mark.accessibility
@pytest.mark.nondestructive
class SocialViewsAccessibilityTest(
    BaseAccessibilityTest, BaseAbstractViewTest, StaticLiveServerTestCase
):
    """
    Accessibility tests for the social views.
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.gamer1.user.username
        self.login_browser()

    def test_community_list(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:community-list")
        )
        assert len(violations) == 0, axe.report(violations)

    def test_my_community_list(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:my-community-list")
        )
        assert len(violations) == 0, axe.report(violations)

    def test_my_application_list(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:my-application-list")
        )
        assert len(violations) == 0, axe.report(violations)

    def test_community_create(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:community-create")
        )
        assert len(violations) == 0, axe.report(violations)

    def test_community_edit(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "gamer_profiles:community-edit",
                kwargs={"community": self.community1.slug},
            )
        )
        assert len(violations) == 0, axe.report(violations)

    def test_community_delete(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "gamer_profiles:community-delete",
                kwargs={"community": self.community1.slug},
            )
        )
        assert len(violations) == 0, axe.report(violations)

    def test_community_member_list(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "gamer_profiles:community-member-list",
                kwargs={"community": self.community1.slug},
            )
        )
        assert len(violations) == 0, axe.report(violations)

    def test_profile_view(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "gamer_profiles:profile-detail",
                kwargs={"gamer": self.gamer1.user.username},
            )
        )
        assert len(violations) == 0, axe.report(violations)

    def test_profile_edit(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:profile-edit")
        )
        assert len(violations) == 0, axe.report(violations)

    def test_add_note(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "gamer_profiles:add-gamer-note", kwargs={"gamer": self.gamer3.username}
            )
        )
        assert len(violations) == 0, axe.report(violations)

    def test_view_friend_requests(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:my-gamer-friend-requests")
        )
        assert len(violations) == 0, axe.report(violations)

    def test_view_block_list(self):
        axe, violations = self.get_axe_violations(
            reverse("gamer_profiles:my-block-list")
        )
        assert len(violations) == 0, axe.report(violations)
