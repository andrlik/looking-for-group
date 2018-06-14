import pytest
from django.db import transaction
from django.core.exceptions import PermissionDenied
from test_plus import TestCase
from ..models import NotInCommunity, AlreadyInCommunity, CommunityMembership, KickedUser, BannedUser
from .factories import GamerProfileWithCommunityFactory, GamerProfileFactory


class FactoryTests(TestCase):
    """
    Tests to ensure factories actually work as expected.
    """

    def setUp(self):
        self.gamer = GamerProfileWithCommunityFactory()

    def test_factory_results(self):
        assert self.gamer.communities.count() == 1


class CommunityFunctionTests(TestCase):
    """
    Actual tests of community functions.
    """

    def setUp(self):
        self.gamer = GamerProfileWithCommunityFactory()
        self.community = self.gamer.communities.all()[0]
        self.gamer2 = GamerProfileFactory()

    def test_community_role(self):
        assert self.gamer.get_role(self.community) == "Member"
        assert self.community.get_role(self.gamer) == "Member"

    def test_community_count(self):
        assert (
            self.community.member_count
            == CommunityMembership.objects.filter(community=self.community).count()
        )

    def test_community_role_for_non_member(self):
        with pytest.raises(NotInCommunity):
            self.gamer2.get_role(self.community)
        with pytest.raises(NotInCommunity):
            self.community.get_role(self.gamer2)

    def test_add_to_community(self):
        assert self.community.member_count == 1
        with transaction.atomic():
            with pytest.raises(AlreadyInCommunity):
                self.community.add_member(self.gamer)
        self.community.add_member(self.gamer2)
        assert self.community.member_count == 2

    def test_remove_member(self):
        with pytest.raises(NotInCommunity):
            self.community.remove_member(self.gamer2)
        self.community.remove_member(self.gamer)
        assert self.community.member_count == 0

    def test_set_role(self):
        assert self.gamer.get_role(self.community) == "Member"
        self.community.set_role(self.gamer, role="admin")
        assert (
            self.gamer.get_role(self.community)
            == "Admin"
            == CommunityMembership.objects.get(
                community=self.community, gamer=self.gamer
            ).get_community_role_display()
        )

    def test_member_list(self):
        self.community.add_member(self.gamer2)
        members = self.community.get_members()
        assert len(members) == 2
        user_list = [self.gamer.pk, self.gamer2.pk]
        for member in members:
            assert member.gamer.pk in user_list

    def test_admin_list(self):
        self.community.add_member(self.gamer2)
        self.community.set_role(self.gamer, role="admin")
        assert self.community.member_count == 2
        assert self.community.get_admins().count() == 1
        assert self.community.get_admins()[0].gamer == self.gamer

    def test_moderator_list(self):
        self.community.add_member(self.gamer2, role='moderator')
        mods = self.community.get_moderators()
        assert mods.count() == 1
        assert mods[0].gamer == self.gamer2

    def test_kick_user_no_delay(self):
        '''
        Delay is enforced in API/Views via rules
        '''
        self.community.add_member(self.gamer2, role='admin')
        self.community.kick_user(self.gamer2, self.gamer, 'Self promotion.')
        assert self.community.member_count == 1
        assert CommunityMembership.objects.filter(gamer=self.gamer).count() == 0
        assert KickedUser.objects.all().count() == 1
        assert KickedUser.objects.all()[0].kicked_user == self.gamer

    def test_kick_non_member(self):
        self.community.set_role(self.gamer, role='admin')
        with pytest.raises(NotInCommunity):
            self.community.kick_user(self.gamer, self.gamer2, 'Premptive strike!')

    def test_not_permitted_kick(self):
        self.community.add_member(self.gamer2)
        with pytest.raises(PermissionDenied):
            self.community.kick_user(self.gamer2, self.gamer, 'We hate him')

    def test_ban_user(self):
        self.community.add_member(self.gamer2, role='admin')
        self.community.ban_user(self.gamer2, self.gamer, 'SPAM and harassment')
        assert self.community.member_count == 1
        assert CommunityMembership.objects.filter(gamer=self.gamer).count() == 0
        assert BannedUser.objects.all().count() == 1
        assert BannedUser.objects.all()[0].banned_user == self.gamer

    def test_ban_non_member(self):
        self.community.set_role(self.gamer, role='admin')
        with pytest.raises(NotInCommunity):
            self.community.ban_user(self.gamer, self.gamer2, 'Sucka@!')

    def test_not_permitted_ban(self):
        self.community.add_member(self.gamer2)
        with pytest.raises(PermissionDenied):
            self.community.ban_user(self.gamer2, self.gamer, 'Revenge!')
