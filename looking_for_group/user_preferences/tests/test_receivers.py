from ...gamer_profiles.models import CommunityMembership, GamerCommunity
from ...gamer_profiles.tests.test_views import AbstractViewTest
from .. import models


class TestAddMember(AbstractViewTest):
    """
    Test that the receiver sets the subscription setting correctly.
    """
    def setUp(self):
        super().setUp()
        self.pref3 = models.Preferences.objects.create(gamer=self.gamer3)
        self.gamer3.refresh_from_db()

    def test_with_default(self):
        self.pref3.community_subscribe_default = True
        self.pref3.save()
        assert self.gamer3.preferences.community_subscribe_default
        self.community1.add_member(self.gamer3)
        assert CommunityMembership.objects.get(gamer=self.gamer3, community=self.community1).game_notifications

    def test_without_default(self):
        self.pref3.community_subscribe_default = False
        self.pref3.save()
        self.community1.add_member(self.gamer3)
        assert not CommunityMembership.objects.get(gamer=self.gamer3, community=self.community1).game_notifications
