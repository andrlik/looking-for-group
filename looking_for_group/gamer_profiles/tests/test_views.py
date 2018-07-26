import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from test_plus import TestCase
from .. import models
from . import factories


class AbstractViewTest(TestCase):
    """
    Does initial setup for all the following tests,
    which will subclass it.
    """

    def setUp(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory(private=False)
        self.community1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.community2 = factories.GamerCommunityFactory(
            owner=factories.GamerProfileFactory(), private=False
        )
        self.community2.add_member(self.gamer2)
        self.gamer3.friends.add(self.gamer1)


class TestSetup(AbstractViewTest):
    """
    Testing that the factory setup above is valid.
    """

    def test_variables(self):
        print(self.gamer1.user.display_name)
        print(self.gamer2.user.display_name)
        print(self.gamer3.user.display_name)
        assert self.community1.get_role(self.gamer1) == "Admin"
        assert self.community2.get_role(self.gamer2) == "Member"
        assert self.gamer1 in self.gamer3.friends.all()


class TestCommunityList(AbstractViewTest):
    """
    Test viewing list of all communities with limited details.
    Note, this does not require any special permissions. However,
    it should be noted that unauthenticated users should not see any
    controls. Private communities should be noted accordingly.
    """

    def test_unauthenticated_view(self):
        self.assertGoodView("gamer_profiles:community-list")
        len(self.get_context("object_list")) == 2

    def test_logged_in_user(self):
        with self.login(username=self.gamer2.user.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseContains("<span class='membership'>Member</span>")
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseContains("<span class='membership'>Admin</span>")
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseNotContains("<span class='membership'>")
            self.assertResponseContains("class='button'>Apply", html=False)
            self.assertResponseContains("class='button'>Join", html=False)


class MyCommunityListView(AbstractViewTest):
    """
    Only a user's communities should be listed.
    """

    def test_unauthenticated_view(self):
        self.assertLoginRequired("gamer_profiles:my-community-list")

    def test_logged_in_user(self):
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("gamer_profiles:my-community-list")
            assert len(self.get_context("object_list")) == 1
        with self.login(username=self.gamer2.user.username):
            self.assertGoodView("gamer_profiles:my-community-list")
            assert len(self.get_context("object_list")) == 1
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView("gamer_profiles:my-community-list")
            assert not self.get_context("object_list")


class CommunityDetailViewTest(AbstractViewTest):
    """
    Test the community detail view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "gamer_profiles:community-detail"

    def test_unauthenticated(self):
        self.assertLoginRequired(self.view_name, community=self.community1.pk)

    def test_authenticated(self):
        with self.login(username=self.gamer1.user.username):
            print(self.community1.pk)
            print(reverse(self.view_name, kwargs={"community": self.community1.pk}))
            assert models.GamerCommunity.objects.get(pk=self.community1.pk)
            self.assertGoodView(self.view_name, community=self.community1.pk)
            self.assertGoodView(self.view_name, community=self.community2.pk)
        with self.login(username=self.gamer2.user.username):
            self.assertGoodView(self.view_name, community=self.community2.pk)
            self.get(self.view_name, self.community1.pk)
            self.response_302()
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(self.view_name, community=self.community2.pk)
            self.get(self.view_name, community=self.community1.pk)
            self.response_302()


class TestCommunityJoinView(AbstractViewTest):
    """
    Test joining a community. Public communities should be
    easily joinable, but privates should redirect to the apply page.
    People who try to join a community they already belong to, are up
    to somethign malicious (since that isn't in the UI), and should be
    denied. Ensure that bans and kicks are enforced.
    """

    def setUp(self):
        super().setUp()
        self.community2.set_role(self.gamer2, role="admin")
        self.form_data = {"confirm": "confirm"}

    def test_login_required(self):
        self.assertLoginRequired(
            "gamer_profiles:community-join", community=self.community2.pk
        )

    def test_private_community(self):
        with self.login(username=self.gamer3.user.username):
            self.get("gamer_profiles:community-join", community=self.community1.pk)
            self.response_302()
            assert "apply" in self.last_response["location"]
            self.post("gamer_profiles:community-join", community=self.community1.pk)
            self.response_302()
            assert "apply" in self.last_response["location"]
            with pytest.raises(models.NotInCommunity):
                self.community1.get_role(self.gamer3)

    def test_public_community(self):
        for user in [self.gamer3.user, self.gamer1.user]:
            with self.login(username=user.username):
                self.assertGoodView(
                    "gamer_profiles:community-join", community=self.community2.pk
                )
                self.post(
                    "gamer_profiles:community-join",
                    data={},
                    community=self.community2.pk,
                )
                self.response_302()
                assert self.community2.get_role(user.gamerprofile)

    def test_join_community_already_in(self):
        with self.login(username=self.gamer2.user.username):
            self.get("gamer_profiles:community-join", community=self.community2.pk)
            self.response_302()

    def test_kicked_user(self):
        self.community2.add_member(self.gamer3)
        self.community2.kick_user(
            kicker=self.gamer2,
            gamer=self.gamer3,
            reason="test",
            earliest_reapply=timezone.now() + timedelta(days=1),
        )
        assert models.KickedUser.objects.filter(
            community=self.community2,
            kicked_user=self.gamer3,
            end_date__gt=timezone.now(),
        )
        with self.login(username=self.gamer3.user.username):
            self.get("gamer_profiles:community-join", community=self.community2.pk)
            self.response_403()
            self.post("gamer_profiles:community-join", community=self.community2.pk)
            self.response_403()
            with pytest.raises(models.NotInCommunity):
                self.community2.get_role(self.gamer3)

    def test_kicked_user_no_date(self):
        self.community2.add_member(self.gamer3)
        self.community2.kick_user(kicker=self.gamer2, gamer=self.gamer3, reason="test")
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(
                "gamer_profiles:community-join", community=self.community2.pk
            )
            self.post("gamer_profiles:community-join", community=self.community2.pk)
            assert self.community2.get_role(self.gamer3) == "Member"

    def test_banned_gamer(self):
        self.community2.add_member(self.gamer3)
        self.community2.ban_user(banner=self.gamer2, gamer=self.gamer3, reason="test")
        assert models.BannedUser.objects.filter(
            banned_user=self.gamer3, community=self.community2
        )
        with self.login(username=self.gamer3.user.username):
            self.get("gamer_profiles:community-join", community=self.community2.pk)
            self.response_403()
            self.post("gamer_profiles:community-join", community=self.community2.pk)
            self.response_403()
            with pytest.raises(models.NotInCommunity):
                self.community2.get_role(self.gamer3)


class TestCommunityApplyView(AbstractViewTest):
    """
    Apply is always available. But not if you are banned or on
    suspension. And if you are already a member, redirect to the community
    detail view without creating an application.
    """

    def setUp(self):
        super().setUp()
        self.apply_data = {"message": "Hi there."}

    def test_login_required(self):
        self.assertLoginRequired(
            "gamer_profiles:community-apply", community=self.community1.pk
        )
        self.post(
            "gamer_profiles:community-apply",
            community=self.community1.pk,
            data=self.apply_data,
        )
        self.response_302()
        assert "login" in self.last_response["location"]

    def test_restrict_suspended_user(self):
        self.community1.add_member(self.gamer3)
        self.community1.kick_user(
            kicker=self.community1.owner,
            gamer=self.gamer3,
            earliest_reapply=timezone.now() + timedelta(days=10),
            reason="annoying",
        )
        with self.login(username=self.gamer3.user.username):
            self.get("gamer_profiles:community-apply", community=self.community1.pk)
            self.response_302()
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            assert current_apps == 0
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
                data=self.apply_data,
            )
            self.response_302()
            assert (
                current_apps
                == models.CommunityApplication.objects.filter(
                    community=self.community1
                ).count()
            )

    def test_restrict_banned_user(self):
        self.community1.add_member(self.gamer3)
        self.community1.ban_user(
            banner=self.community1.owner, gamer=self.gamer3, reason="Harassment"
        )
        with self.login(username=self.gamer3.user.username):
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            self.get("gamer_profiles:community-apply", community=self.community1.pk)
            self.response_302()
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
                data=self.apply_data,
            )
            self.response_302()
            assert (
                current_apps
                == models.CommunityApplication.objects.filter(
                    community=self.community1
                ).count()
            )

    def test_normal_user(self):
        with self.login(username=self.gamer3.user.username):
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            assert current_apps == 0
            self.assertGoodView(
                "gamer_profiles:community-apply", community=self.community1.pk
            )
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
                data=self.apply_data,
            )
            self.response_302()
            assert (
                current_apps
                < models.CommunityApplication.objects.filter(
                    community=self.community1
                ).count()
            )

    def test_user_kicked_no_suspension(self):
        self.community1.add_member(self.gamer3)
        self.community1.kick_user(
            kicker=self.community1.owner, gamer=self.gamer3, reason="Bam!"
        )
        self.test_normal_user()


class UpdateApplicationTest(AbstractViewTest):
    """
    Test that only the author of an application can edit its message.
    """

    def setUp(self):
        super().setUp()
        self.application = models.CommunityApplication.objects.create(
            gamer=self.gamer3, message="Not me", community=self.community1, status="new"
        )
        self.update_data = {"message": "This is better"}

    def test_login_required(self):
        self.assertLoginRequired(
            "gamer_profiles:update-application", application=self.application.pk
        )

    def test_non_owner(self):
        with self.login(username=self.gamer2.user.username):
            self.get(
                "gamer_profiles:update-application", application=self.application.pk
            )
            self.response_302()
            self.post(
                "gamer_profiles:update-application",
                application=self.application.pk,
                data=self.update_data,
            )
            self.response_302()
            assert (
                models.CommunityApplication.objects.get(pk=self.application.pk).message
                == "Not me"
            )

    def test_owner(self):
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(
                "gamer_profiles:update-application", application=self.application.pk
            )
            self.post(
                "gamer_profiles:update-application",
                application=self.application.pk,
                data=self.update_data,
            )
            self.response_302()
            assert (
                models.CommunityApplication.objects.get(pk=self.application.pk).message
                == "This is better"
            )
