import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

from ...game_catalog.tests.test_accessibility import BaseAccessibilityTest
from ..models import Invite
from ..tests.test_views import AbstractInviteTestCase


@pytest.mark.accessibility
@pytest.mark.nondestructive
class InviteAccessibilityTest(BaseAccessibilityTest, AbstractInviteTestCase, StaticLiveServerTestCase):
    """
    Invite accessibility
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.gamer1.user.username
        self.invite1 = Invite.objects.create(label="test_game_invite", content_object=self.gp1, creator=self.gamer3.user)
        self.login_browser()

    def test_invite_create(self):
        axe, violations = self.get_axe_violations(reverse("invites:invite_create", kwargs={"content_type": ContentType.objects.get_for_model(self.gp1).pk, "slug": self.gp1.slug}))
        assert len(violations) == 0, axe.report(violations)

    def test_invite_accept_view(self):
        axe, violations = self.get_axe_violations(reverse("invites:invite_accept", kwargs={"invite": self.invite1.slug}))
        assert len(violations) == 0, axe.report(violations)

    def test_invite_delete_view(self):
        axe, violations = self.get_axe_violations(reverse("invites:invite_delete", kwargs={"invite": self.invite1.slug}))
        assert len(violations) == 0, axe.report(violations)
