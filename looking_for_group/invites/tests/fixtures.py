from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory
from ...games.models import GamePosting, Player
from ..models import Invite


class InviteTData(object):
    def __init__(self):
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.gamer4 = GamerProfileFactory()
        self.gamer5 = GamerProfileFactory()
        self.comm1 = GamerCommunityFactory(owner=self.gamer1)
        self.comm2 = GamerCommunityFactory(owner=self.gamer2)
        self.comm3 = GamerCommunityFactory(owner=self.gamer3)
        self.comm1.add_member(self.gamer4, role="moderator")
        self.comm1.add_member(self.gamer3, role="member")
        self.comm2.add_member(self.gamer4, role="moderator")
        self.comm3.add_member(self.gamer1)
        self.comm3.add_member(self.gamer4, role="moderator")
        self.comm2.invites_allowed = "moderator"
        self.comm2.save()
        self.comm1.invites_allowed = "member"
        self.comm1.save()
        self.gp1 = GamePosting.objects.create(
            title="the long dark tea time of the soul",
            gm=self.gamer3,
            game_description="Lots of spoooooooky stuff",
        )
        self.player1 = Player.objects.create(gamer=self.gamer2, game=self.gp1)
        self.admin_url_kwargs = {
            "content_type": ContentType.objects.get_for_model(self.comm3).id,
            "slug": self.comm3.slug,
        }
        self.mod_url_kwargs = {
            "content_type": ContentType.objects.get_for_model(self.comm2).id,
            "slug": self.comm2.slug,
        }
        self.mem_url_kwargs = {
            "content_type": ContentType.objects.get_for_model(self.comm1).id,
            "slug": self.comm1.slug,
        }
        self.game_url_kwargs = {
            "content_type": ContentType.objects.get_for_model(self.gp1).pk,
            "slug": self.gp1.slug,
        }
        self.invite1 = Invite.objects.create(label="test_game_invite", content_object=self.gp1, creator=self.gamer3.user)
        self.invite2 = Invite(
            label="community_test_invite",
            content_object=self.comm1,
            creator=self.gamer3.user,
        )
        self.invite2.save()
        self.invite3 = Invite(
            label="community_test_invite_dos",
            content_object=self.comm1,
            creator=self.gamer1.user,
        )
        self.invite3.save()
        self.expired_invite = Invite.objects.create(label="expired_invite", content_object=self.gp1, creator=self.gamer3.user)
        self.expired_invite.expires = timezone.now() - timedelta(days=2)
        self.expired_invite.status = "expired"
        self.expired_invite.save()
        self.accepted_invite = Invite.objects.create(label="accepted_invite", content_object=self.gp1, creator=self.gamer3.user, status="accepted", accepted_by=self.gamer2.user)


@pytest.fixture
def invite_testdata():
    ContentType.objects.clear_cache()
    yield InviteTData()
    ContentType.objects.clear_cache()
