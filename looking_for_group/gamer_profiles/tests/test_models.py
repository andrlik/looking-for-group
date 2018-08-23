import pytest
import factory.django
from django.db import transaction
from django.db.models.signals import post_save
from django.core.exceptions import PermissionDenied
from test_plus import TestCase
from ..models import NotInCommunity, AlreadyInCommunity, CommunityMembership, KickedUser, BannedUser, GamerFriendRequest
from .factories import GamerProfileWithCommunityFactory, GamerProfileFactory, GamerCommunityFactory


class FactoryTests(TestCase):
    """
    Tests to ensure factories actually work as expected.
    """

    def setUp(self):
        with factory.django.mute_signals(post_save):
            self.gamer = GamerProfileWithCommunityFactory()
            self.gamer2 = GamerProfileFactory()
            print(self.gamer.user.display_name)
            print(self.gamer2.user.display_name)

    def test_factory_results(self):
        assert self.gamer.communities.count() == 1

    def test_user_created(self):
        assert self.gamer.user

    def test_user_without_community(self):
        assert self.gamer2.user


class CommunityFunctionTests(TestCase):
    """
    Actual tests of community functions.
    """

    def setUp(self):
        self.gamer = GamerProfileFactory()
        self.community = GamerCommunityFactory(owner=GamerProfileFactory())
        self.community.add_member(self.gamer)
        self.community.refresh_from_db()
        self.gamer2 = GamerProfileFactory()
        print(self.gamer.user.display_name)
        print(self.gamer2.user.display_name)

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
        assert self.community.member_count == 2
        with transaction.atomic():
            with pytest.raises(AlreadyInCommunity):
                self.community.add_member(self.gamer)
        self.community.add_member(self.gamer2)
        self.community.refresh_from_db()
        assert self.community.member_count == 3

    def test_remove_member(self):
        with pytest.raises(NotInCommunity):
            self.community.remove_member(self.gamer2)
        self.community.remove_member(self.gamer)
        self.community.refresh_from_db()
        assert self.community.member_count == 1

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
        assert len(members) == 3
        user_list = [self.community.owner.pk, self.gamer.pk, self.gamer2.pk]
        for member in members:
            assert member.gamer.pk in user_list

    def test_admin_list(self):
        self.community.add_member(self.gamer2)
        self.community.refresh_from_db()
        self.community.set_role(self.gamer, role="admin")
        assert self.community.member_count == 3
        assert self.community.get_admins().count() == 2

    def test_moderator_list(self):
        self.community.add_member(self.gamer2, role='moderator')
        self.community.refresh_from_db()
        mods = self.community.get_moderators()
        assert mods.count() == 1
        assert mods[0].gamer == self.gamer2

    def test_kick_user_no_delay(self):
        '''
        Delay is enforced in API/Views via rules
        '''
        self.community.add_member(self.gamer2, role='admin')
        self.community.kick_user(self.gamer2, self.gamer, 'Self promotion.')
        self.community.refresh_from_db()
        assert self.community.member_count == 2
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
        self.community.refresh_from_db()
        assert self.community.member_count == 2
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


class TestFriendships(TestCase):
    '''
    Test friend requests for other users.
    '''

    def setUp(self):
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()

    def test_friend_requests_check(self):
        assert self.gamer1.friend_requests_received.count() == 0
        assert self.gamer1.friend_requests_sent.count() == 0
        req = GamerFriendRequest.objects.create(requestor=self.gamer1, recipient=self.gamer2)
        assert req.status == 'new'
        assert self.gamer1.friend_requests_sent.count() == 1
        assert self.gamer2.friend_requests_received.count() == 1

    def test_accept_friend_request(self):
        assert self.gamer1.friends.count() == self.gamer2.friends.count() and self.gamer1.friends.count() == 0
        req = GamerFriendRequest.objects.create(requestor=self.gamer1, recipient=self.gamer2)
        req.accept()
        assert self.gamer1.friends.all().count() == 1
        assert self.gamer1.friends.all()[0] == self.gamer2
        assert self.gamer2.friends.all().count() == 1
        assert GamerFriendRequest.objects.get(pk=req.pk).status == 'accept'

    def test_reject_friendship(self):
        req = GamerFriendRequest.objects.create(requestor=self.gamer1, recipient=self.gamer2)
        req.deny()
        assert self.gamer1.friends.count() == 0
        assert GamerFriendRequest.objects.get(pk=req.pk).status == 'reject'


class TestRoleComparisons(TestCase):
    '''
    Test whether roles are compared correctly.
    '''

    def setUp(self):
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.community1 = GamerCommunityFactory(owner=self.gamer1)
        self.community1.add_member(self.gamer2, 'moderator')
        self.community1.add_member(self.gamer3)
        self.gamer1_membership = CommunityMembership.objects.get(gamer=self.gamer1, community=self.community1)
        self.gamer2_membership = CommunityMembership.objects.get(gamer=self.gamer2, community=self.community1)
        self.gamer3_membership = CommunityMembership.objects.get(gamer=self.gamer3, community=self.community1)

    def test_invalid_role_comparison(self):
        with pytest.raises(ValueError):
            self.gamer1_membership.less_than('god')

    def test_comparisons(self):
        for role in ['admin', 'moderator', 'member']:
            assert not self.gamer1_membership.less_than(role)
        assert self.gamer2_membership.less_than('admin')
        for role in ['moderator', 'member']:
            assert not self.gamer2_membership.less_than(role)
        for role in ['admin', 'moderator']:
            assert self.gamer3_membership.less_than(role)
        assert not self.gamer3_membership.less_than('member')
