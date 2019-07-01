import pytest
from django.core.exceptions import PermissionDenied
from django.db import transaction

from ..models import AlreadyInCommunity, BannedUser, CommunityMembership, GamerFriendRequest, KickedUser, NotInCommunity
from .factories import GamerProfileFactory, GamerProfileWithCommunityFactory

pytestmark = pytest.mark.django_db(transaction=True)


def test_factory_profile_with_community():
    gamer = GamerProfileWithCommunityFactory()
    assert gamer.user
    assert gamer.communities.count() == 1


def test_factory_profile_only():
    gamer = GamerProfileFactory()
    assert gamer.user


def test_community_role(social_testdata):
    assert social_testdata.gamer1.get_role(social_testdata.community) == "Member"
    assert social_testdata.community.get_role(social_testdata.gamer1) == "Member"


def test_community_count(social_testdata):
    assert (
        social_testdata.community.member_count
        == CommunityMembership.objects.filter(
            community=social_testdata.community
        ).count()
    )


def test_community_role_for_non_member(social_testdata):
    with pytest.raises(NotInCommunity):
        social_testdata.gamer2.get_role(social_testdata.community)
    with pytest.raises(NotInCommunity):
        social_testdata.community.get_role(social_testdata.gamer2)


def test_add_to_community(social_testdata):
    assert social_testdata.community.member_count == 2
    with transaction.atomic():
        with pytest.raises(AlreadyInCommunity):
            social_testdata.community.add_member(social_testdata.gamer1)
    social_testdata.community.add_member(social_testdata.gamer2)
    social_testdata.community.refresh_from_db()
    assert social_testdata.community.member_count == 3


def test_remove_member(social_testdata):
    with pytest.raises(NotInCommunity):
        social_testdata.community.remove_member(social_testdata.gamer2)
    social_testdata.community.remove_member(social_testdata.gamer1)
    social_testdata.community.refresh_from_db()
    assert social_testdata.community.member_count == 1


def test_set_role(social_testdata):
    assert social_testdata.gamer1.get_role(social_testdata.community) == "Member"
    social_testdata.community.set_role(social_testdata.gamer1, role="admin")
    assert (
        social_testdata.gamer1.get_role(social_testdata.community)
        == "Admin"
        == CommunityMembership.objects.get(
            community=social_testdata.community, gamer=social_testdata.gamer1
        ).get_community_role_display()
    )


def test_member_list(social_testdata):
    social_testdata.community.add_member(social_testdata.gamer2)
    members = social_testdata.community.get_members()
    assert len(members) == 3
    user_list = [
        social_testdata.community.owner.pk,
        social_testdata.gamer1.pk,
        social_testdata.gamer2.pk,
    ]
    for member in members:
        assert member.gamer.pk in user_list


def test_admin_list(social_testdata):
    social_testdata.community.add_member(social_testdata.gamer2)
    social_testdata.community.refresh_from_db()
    social_testdata.community.set_role(social_testdata.gamer1, role="admin")
    assert social_testdata.community.member_count == 3
    assert social_testdata.community.get_admins().count() == 2


def test_moderator_list(social_testdata):
    social_testdata.community.add_member(social_testdata.gamer2, role="moderator")
    social_testdata.community.refresh_from_db()
    mods = social_testdata.community.get_moderators()
    assert mods.count() == 1
    assert mods[0].gamer == social_testdata.gamer2


def test_kick_user_no_delay(social_testdata):
    """
    Delay is enforced in API/Views via rules
    """
    social_testdata.community.add_member(social_testdata.gamer2, role="admin")
    social_testdata.community.kick_user(
        social_testdata.gamer2, social_testdata.gamer1, "Self promotion."
    )
    social_testdata.community.refresh_from_db()
    assert social_testdata.community.member_count == 2
    assert CommunityMembership.objects.filter(gamer=social_testdata.gamer1).count() == 2
    assert KickedUser.objects.all().count() == 1
    assert KickedUser.objects.all()[0].kicked_user == social_testdata.gamer1


def test_kick_non_member(social_testdata):
    social_testdata.community.set_role(social_testdata.gamer1, role="admin")
    with pytest.raises(NotInCommunity):
        social_testdata.community.kick_user(
            social_testdata.gamer1, social_testdata.gamer2, "Premptive strike!"
        )


def test_not_permitted_kick(social_testdata):
    social_testdata.community.add_member(social_testdata.gamer2)
    with pytest.raises(PermissionDenied):
        social_testdata.community.kick_user(
            social_testdata.gamer2, social_testdata.gamer1, "We hate him"
        )


def test_ban_user(social_testdata):
    social_testdata.community.add_member(social_testdata.gamer2, role="admin")
    social_testdata.community.ban_user(
        social_testdata.gamer2, social_testdata.gamer1, "SPAM and harassment"
    )
    social_testdata.community.refresh_from_db()
    assert social_testdata.community.member_count == 2
    assert CommunityMembership.objects.filter(gamer=social_testdata.gamer1).count() == 2
    assert BannedUser.objects.all().count() == 1
    assert BannedUser.objects.all()[0].banned_user == social_testdata.gamer1


def test_ban_non_member(social_testdata):
    social_testdata.community.set_role(social_testdata.gamer1, role="admin")
    with pytest.raises(NotInCommunity):
        social_testdata.community.ban_user(
            social_testdata.gamer1, social_testdata.gamer2, "Sucka@!"
        )


def test_not_permitted_ban(social_testdata):
    social_testdata.community.add_member(social_testdata.gamer2)
    with pytest.raises(PermissionDenied):
        social_testdata.community.ban_user(
            social_testdata.gamer2, social_testdata.gamer1, "Revenge!"
        )


def test_friend_requests_check(social_testdata):
    assert social_testdata.gamer1.friend_requests_received.count() == 1
    assert social_testdata.gamer1.friend_requests_sent.count() == 0
    req = GamerFriendRequest.objects.create(
        requestor=social_testdata.gamer1, recipient=social_testdata.gamer2
    )
    assert req.status == "new"
    assert social_testdata.gamer1.friend_requests_sent.count() == 1
    assert social_testdata.gamer2.friend_requests_received.count() == 1


def test_accept_friend_request(social_testdata):
    assert (
        social_testdata.gamer1.friends.count() > social_testdata.gamer2.friends.count()
        and social_testdata.gamer1.friends.count() == 1
    )
    req = GamerFriendRequest.objects.create(
        requestor=social_testdata.gamer1, recipient=social_testdata.gamer2
    )
    req.accept()
    assert social_testdata.gamer1.friends.all().count() == 2
    assert social_testdata.gamer2 in social_testdata.gamer1.friends.all()
    assert social_testdata.gamer2.friends.all().count() == 1
    assert GamerFriendRequest.objects.get(pk=req.pk).status == "accept"


def test_reject_friendship(social_testdata):
    req = GamerFriendRequest.objects.create(
        requestor=social_testdata.gamer1, recipient=social_testdata.gamer2
    )
    req.deny()
    assert social_testdata.gamer1.friends.count() == 1
    assert GamerFriendRequest.objects.get(pk=req.pk).status == "reject"


def test_invalid_role_comparison(social_testdata):
    with pytest.raises(ValueError):
        CommunityMembership.objects.get(
            gamer=social_testdata.gamer1, community=social_testdata.community1
        ).less_than("god")


def test_comparisons(social_testdata):
    social_testdata.community1.add_member(social_testdata.gamer2, "moderator")
    social_testdata.community1.add_member(social_testdata.gamer3)
    gamer1_membership = CommunityMembership.objects.get(
        gamer=social_testdata.gamer1, community=social_testdata.community1
    )
    gamer2_membership = CommunityMembership.objects.get(
        gamer=social_testdata.gamer2, community=social_testdata.community1
    )
    gamer3_membership = CommunityMembership.objects.get(
        gamer=social_testdata.gamer3, community=social_testdata.community1
    )
    for role in ["admin", "moderator", "member"]:
        assert not gamer1_membership.less_than(role)
    assert gamer2_membership.less_than("admin")
    for role in ["moderator", "member"]:
        assert not gamer2_membership.less_than(role)
    for role in ["admin", "moderator"]:
        assert gamer3_membership.less_than(role)
    assert not gamer3_membership.less_than("member")
