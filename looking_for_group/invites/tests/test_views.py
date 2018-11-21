from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from test_plus import TestCase

from ...gamer_profiles.models import CommunityMembership
from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory
from ...games.models import GamePosting, Player
from ..models import Invite


class AbstractInviteTestCase(TestCase):
    """
    Makes setup less redundant.
    """

    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.gamer4 = GamerProfileFactory()
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
            gm=self.gamer1,
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

    def tearDown(self):
        ContentType.objects.clear_cache()
        super().tearDown()


class TestInviteCreateView(AbstractInviteTestCase):
    """
    Test invite creation
    """

    def setUp(self):
        super().setUp()
        self.view_name = "invites:invite_create"
        self.post_data = {"label": "test invite"}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.mem_url_kwargs)

    def test_member_invite_not_allowed(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.mod_url_kwargs)
            self.response_403()
            self.get(self.view_name, **self.admin_url_kwargs)
            self.response_403()
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.mod_url_kwargs)
            self.get(self.view_name, **self.admin_url_kwargs)
            self.response_403()

    def test_member_invite_allowed(self):
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_name, **self.mem_url_kwargs)

    def test_admin_allowed(self):
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_name, **self.admin_url_kwargs)

    def test_game_invite_allowed(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.game_url_kwargs)
            self.response_403()
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.game_url_kwargs)

    def test_create_community_invite(self):
        with self.login(username=self.gamer1.username):
            invite_count = Invite.objects.count()
            self.post(self.view_name, data=self.post_data, **self.mem_url_kwargs)
            self.response_302()
            assert Invite.objects.count() - invite_count == 1

    def test_create_game_invite(self):
        with self.login(username=self.gamer1.username):
            invite_count = Invite.objects.count()
            self.post(self.view_name, data=self.post_data, **self.game_url_kwargs)
            self.response_302()
            assert Invite.objects.count() - invite_count == 1


class InviteDeletionTest(AbstractInviteTestCase):
    """
    Tests deletion of invites, so we'll create a few here.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "invites:invite_delete"
        self.invite1 = Invite(
            label="test_game_invite", content_object=self.gp1, creator=self.gamer1.user
        )
        self.invite1.save()
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

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, invite=self.invite1.slug)

    def test_non_gm_game_delete(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, invite=self.invite1.slug)
            self.response_403()

    def test_gm_game_delete(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, invite=self.invite1.slug)

    def test_delete_game_invite(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data={}, invite=self.invite1.slug)
            with pytest.raises(ObjectDoesNotExist):
                Invite.objects.get(pk=self.invite1.pk)

    def test_delete_own_community_invite(self):
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_name, invite=self.invite2.slug)
            self.post(self.view_name, data={}, invite=self.invite2.slug)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                Invite.objects.get(pk=self.invite2.pk)

    def test_delete_other_user_invite(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, invite=self.invite3.slug)
            self.response_403()
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, invite=self.invite2.slug)
            self.post(self.view_name, data={}, invite=self.invite2.slug)
            self.response_302()


class InviteAcceptTest(AbstractInviteTestCase):
    """
    Testing acceptance of invites.
    Note, this only tests the internal process. For apps that use this,
    tests should be written for their relevant receivers. Any example
    checking here is purely educational and not intended to be comprehensive.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "invites:invite_accept"
        self.post_data = {"status": "accepted"}
        self.bad_post_data = {"status": "expired"}
        self.invite1 = Invite(
            label="test_game_invite", content_object=self.gp1, creator=self.gamer1.user
        )
        self.invite1.save()
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
        self.gamer5 = GamerProfileFactory()

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, invite=self.invite1.slug)
        self.assertLoginRequired(self.view_name, invite=self.invite2.slug)

    def test_page_load_valid(self):
        with self.login(username=self.gamer5.username):
            self.assertGoodView(self.view_name, invite=self.invite1.slug)

    def test_page_load_accepted(self):
        self.invite1.status = "accepted"
        self.invite1.accepted_by = self.gamer4.user
        self.invite1.save()
        with self.login(username=self.gamer5.username):
            self.get(self.view_name, invite=self.invite1.slug)
            self.response_302()
        self.invite1.refresh_from_db()
        assert self.invite1.status == "accepted"

    def test_page_load_expired(self):
        self.invite1.expires_at = timezone.now() - timedelta(days=10)
        self.invite1.save()
        with self.login(username=self.gamer5.username):
            self.get(self.view_name, invite=self.invite1.slug)
            self.response_302()
        self.invite1.refresh_from_db()
        assert self.invite1.status == "expired"

    def test_invalid_post_data(self):
        with self.login(username=self.gamer5.username):
            self.post(self.view_name, data=self.bad_post_data, invite=self.invite1.slug)
            self.response_200()
            assert Invite.objects.get(pk=self.invite1.pk).status == "pending"

    def test_valid_post_data_game(self):
        with self.login(username=self.gamer5.username):
            self.post(self.view_name, data=self.post_data, invite=self.invite1.slug)
            self.response_302()
            self.invite1.refresh_from_db()
            assert self.invite1.status == "accepted"
            assert self.invite1.accepted_by == self.gamer5.user
            assert Player.objects.get(game=self.gp1, gamer=self.gamer5)

    def test_valid_post_data_community(self):
        with self.login(username=self.gamer5.username):
            self.post(self.view_name, data=self.post_data, invite=self.invite2.slug)
            self.response_302()
            self.invite2.refresh_from_db()
            assert self.invite2.status == "accepted"
            assert self.invite2.accepted_by == self.gamer5.user
            assert CommunityMembership.objects.get(
                community=self.comm1, gamer=self.gamer5
            )

    def test_already_in_game(self):
        """
        This should proceed silently without error.
        """
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.post_data, invite=self.invite1.slug)
            self.response_302()
            self.invite1.refresh_from_db()
            assert self.invite1.status == "accepted"
            assert self.invite1.accepted_by == self.gamer2.user

    def test_already_in_community(self):
        """
        This should fail silently without error.
        """
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, invite=self.invite2.slug)
            self.response_302()
            self.invite2.refresh_from_db()
            assert self.invite2.status == "accepted"
            assert self.invite2.accepted_by == self.gamer1.user
