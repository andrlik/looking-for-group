from datetime import timedelta

import pytest
from django.utils import timezone

from .. import models
from ..tests import factories


class SocialTData(object):
    def __init__(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory(private=False)
        self.gamer4 = factories.GamerProfileFactory()
        self.gamer5 = factories.GamerProfileFactory()
        self.gamer6 = factories.GamerProfileFactory()
        self.public_gamer = factories.GamerProfileFactory()
        self.public_gamer.private = False
        self.public_gamer.save()
        self.blocked_gamer = factories.GamerProfileFactory()
        self.block_record = models.BlockedUser.objects.create(
            blocker=self.gamer1, blockee=self.blocked_gamer
        )
        self.muted_gamer = factories.GamerProfileFactory()
        self.mute_record = models.MutedUser.objects.create(
            muter=self.gamer1, mutee=self.muted_gamer
        )
        self.community = factories.GamerCommunityFactory(owner=self.gamer5)
        self.community.set_role(self.gamer5, "admin")
        self.community.add_member(self.gamer1)
        self.community1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.community1.set_role(self.gamer1, "admin")
        self.community1.add_member(self.blocked_gamer)
        self.community2 = factories.GamerCommunityFactory(
            owner=self.gamer5, private=False
        )
        self.community2.add_member(self.gamer2)
        self.community_public = factories.GamerCommunityFactory(
            owner=self.gamer3, private=False
        )
        self.community_public.add_member(self.gamer1)
        self.community_public.add_member(self.gamer6)
        self.gamer3.friends.add(self.gamer1)
        self.prospective_friend = factories.GamerProfileFactory()
        self.fr = models.GamerFriendRequest.objects.create(
            requestor=self.prospective_friend, recipient=self.gamer1, status="new"
        )
        self.gn = models.GamerNote.objects.create(
            gamer=self.gamer3,
            author=self.gamer1,
            title="Test note",
            body="This is someone new.",
        )


class SocialTDataKicks(SocialTData):
    def __init__(self):
        super().__init__()
        self.community1.add_member(self.gamer2)
        self.kick1 = self.community1.kick_user(
            kicker=self.gamer1, gamer=self.gamer2, reason="Bad apple"
        )
        self.community1.add_member(self.gamer3)
        self.kick2 = self.community1.kick_user(
            kicker=self.gamer1,
            gamer=self.gamer3,
            reason="Jerk",
            earliest_reapply=timezone.now() + timedelta(days=30),
        )
        self.community2.set_role(self.gamer2, "admin")
        self.community2.add_member(self.gamer3)
        self.kick3 = self.community2.kick_user(
            kicker=self.gamer2,
            gamer=self.gamer3,
            reason="test",
            earliest_reapply=timezone.now() + timedelta(days=10),
        )
        assert models.KickedUser.objects.filter(
            community=self.community2,
            kicked_user=self.gamer3,
            end_date__gt=timezone.now(),
        )
        self.community.add_member(self.gamer4)
        self.banned1 = self.community.ban_user(
            banner=self.community.owner, gamer=self.gamer4, reason="Test"
        )
        assert models.BannedUser.objects.filter(
            banned_user=self.gamer4, community=self.community
        )
        self.new_gamer = factories.GamerProfileFactory()
        self.application = models.CommunityApplication.objects.create(
            community=self.community1,
            gamer=self.new_gamer,
            message="Hi there. Can I play too?",
            status="review",
        )


@pytest.fixture
def social_testdata(transactional_db):
    return SocialTData()


@pytest.fixture
def social_testdata_with_kicks(transactional_db):
    return SocialTDataKicks()


@pytest.fixture
def social_community_slug(social_testdata):
    return social_testdata.community1.slug


@pytest.fixture
def social_gamer_to_check(social_testdata):
    return social_testdata.gamer1
