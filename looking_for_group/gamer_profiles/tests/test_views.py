from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from test_plus import TestCase

from . import factories
from .. import models


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
        print(self.gamer1.display_name)
        print(self.gamer2.display_name)
        print(self.gamer3.display_name)
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
        with self.login(username=self.gamer2.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseContains("<span class='membership'>Member</span>")
        with self.login(username=self.gamer1.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseContains("<span class='membership'>Admin</span>")
        with self.login(username=self.gamer3.username):
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
        with self.login(username=self.gamer1.username):
            self.assertGoodView("gamer_profiles:my-community-list")
            assert len(self.get_context("object_list")) == 1
        with self.login(username=self.gamer2.username):
            self.assertGoodView("gamer_profiles:my-community-list")
            assert len(self.get_context("object_list")) == 1
        with self.login(username=self.gamer3.username):
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
        self.assertLoginRequired(self.view_name, community=self.community1.slug)

    def test_authenticated(self):
        with self.login(username=self.gamer1.username):
            print(self.community1.pk)
            print(reverse(self.view_name, kwargs={"community": self.community1.slug}))
            assert models.GamerCommunity.objects.get(pk=self.community1.pk)
            self.assertGoodView(self.view_name, community=self.community1.slug)
            self.assertGoodView(self.view_name, community=self.community2.slug)
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, community=self.community2.slug)
            self.get(self.view_name, self.community1.slug)
            self.response_302()
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_name, community=self.community2.slug)
            self.get(self.view_name, community=self.community1.slug)
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
            "gamer_profiles:community-join", community=self.community2.slug
        )

    def test_private_community(self):
        with self.login(username=self.gamer3.username):
            self.get("gamer_profiles:community-join", community=self.community1.slug)
            self.response_302()
            assert "apply" in self.last_response["location"]
            self.post("gamer_profiles:community-join", community=self.community1.slug)
            self.response_302()
            assert "apply" in self.last_response["location"]
            with pytest.raises(models.NotInCommunity):
                self.community1.get_role(self.gamer3)

    def test_public_community(self):
        for user in [self.gamer3.user, self.gamer1.user]:
            with self.login(username=user.username):
                self.assertGoodView(
                    "gamer_profiles:community-join", community=self.community2.slug
                )
                self.post(
                    "gamer_profiles:community-join",
                    data={},
                    community=self.community2.slug,
                )
                self.response_302()
                assert self.community2.get_role(user.gamerprofile)

    def test_join_community_already_in(self):
        with self.login(username=self.gamer2.username):
            self.get("gamer_profiles:community-join", community=self.community2.slug)
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
        with self.login(username=self.gamer3.username):
            self.get("gamer_profiles:community-join", community=self.community2.slug)
            self.response_403()
            self.post("gamer_profiles:community-join", community=self.community2.slug)
            self.response_403()
            with pytest.raises(models.NotInCommunity):
                self.community2.get_role(self.gamer3)

    def test_kicked_user_no_date(self):
        self.community2.add_member(self.gamer3)
        self.community2.kick_user(kicker=self.gamer2, gamer=self.gamer3, reason="test")
        with self.login(username=self.gamer3.username):
            self.assertGoodView(
                "gamer_profiles:community-join", community=self.community2.slug
            )
            self.post("gamer_profiles:community-join", community=self.community2.slug)
            assert self.community2.get_role(self.gamer3) == "Member"

    def test_banned_gamer(self):
        self.community2.add_member(self.gamer3)
        self.community2.ban_user(banner=self.gamer2, gamer=self.gamer3, reason="test")
        assert models.BannedUser.objects.filter(
            banned_user=self.gamer3, community=self.community2
        )
        with self.login(username=self.gamer3.username):
            self.get("gamer_profiles:community-join", community=self.community2.slug)
            self.response_403()
            self.post("gamer_profiles:community-join", community=self.community2.slug)
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
            "gamer_profiles:community-apply", community=self.community1.slug
        )
        self.post(
            "gamer_profiles:community-apply",
            community=self.community1.slug,
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
        with self.login(username=self.gamer3.username):
            self.get("gamer_profiles:community-apply", community=self.community1.slug)
            self.response_403()
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            assert current_apps == 0
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.slug,
                data=self.apply_data,
            )
            self.response_403()
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
        with self.login(username=self.gamer3.username):
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            self.get("gamer_profiles:community-apply", community=self.community1.slug)
            self.response_403()
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.slug,
                data=self.apply_data,
            )
            self.response_403()
            assert (
                current_apps
                == models.CommunityApplication.objects.filter(
                    community=self.community1
                ).count()
            )

    def test_normal_user(self):
        with self.login(username=self.gamer3.username):
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            assert current_apps == 0
            self.assertGoodView(
                "gamer_profiles:community-apply", community=self.community1.slug
            )
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.slug,
                data=self.apply_data,
            )
            self.response_302()
            assert (
                current_apps
                < models.CommunityApplication.objects.filter(
                    community=self.community1
                ).count()
            )

    def test_normal_user_submit(self):
        with self.login(username=self.gamer3.username):
            submit_data = self.apply_data
            submit_data["submit_app"] = ""
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.slug,
                data=submit_data,
            )
            self.response_302()
            assert (
                models.CommunityApplication.objects.filter(
                    community=self.community1, gamer=self.gamer3
                )
                .order_by("-modified")[0]
                .status
                == "review"
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
        with self.login(username=self.gamer2.username):
            self.get(
                "gamer_profiles:update-application", application=self.application.pk
            )
            self.response_403()
            self.post(
                "gamer_profiles:update-application",
                application=self.application.pk,
                data=self.update_data,
            )
            self.response_403()
            assert (
                models.CommunityApplication.objects.get(pk=self.application.pk).message
                == "Not me"
            )

    def test_owner(self):
        with self.login(username=self.gamer3.username):
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

    def test_owner_submit(self):
        with self.login(username=self.gamer3.username):
            submit_data = self.update_data
            submit_data["submit_app"] = ""
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.slug,
                data=submit_data,
            )
            self.response_302()
            assert (
                models.CommunityApplication.objects.filter(
                    community=self.community1, gamer=self.gamer3
                )
                .order_by("-modified")[0]
                .status
                == "review"
            )


class CommunityApplicationWithdrawTest(AbstractViewTest):
    """
    Test withdraw/delete view for Community Application objects.
    """

    def setUp(self):
        super().setUp()
        self.application = models.CommunityApplication.objects.create(
            gamer=self.gamer3, message="Not me", community=self.community1, status="new"
        )

    def test_login_required(self):
        self.assertLoginRequired(
            "gamer_profiles:delete-application", application=self.application.pk
        )

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(
                "gamer_profiles:delete-application", application=self.application.pk
            )
            self.response_403()
            self.post(
                "gamer_profiles:delete-application", application=self.application.pk
            )
            self.response_403()
            assert models.CommunityApplication.objects.get(pk=self.application.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer3.username):
            self.assertGoodView(
                "gamer_profiles:delete-application", application=self.application.pk
            )
            self.post(
                "gamer_profiles:delete-application", application=self.application.pk
            )
            with pytest.raises(ObjectDoesNotExist):
                models.CommunityApplication.objects.get(pk=self.application.pk)


class CommunityApplicantListTest(AbstractViewTest):
    """
    Test a community moderator ability to see pending applications.
    """

    def setUp(self):
        super().setUp()
        self.application1 = models.CommunityApplication.objects.create(
            gamer=self.gamer3,
            message="Notice me, Senpai!",
            community=self.community1,
            status="review",
        )
        self.application2 = models.CommunityApplication.objects.create(
            gamer=self.gamer2,
            message="I want to play!",
            community=self.community1,
            status="new",
        )
        self.view_str = "gamer_profiles:community-applicant-list"
        self.url_kwargs = {"community": self.community1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            applicants = self.get_context("applicants")
            assert len(applicants) == 1
            self.application2.submit_application()
            self.assertGoodView(self.view_str, **self.url_kwargs)
            assert len(self.get_context("applicants")) == 2


class CommunityApplicationDetail(AbstractViewTest):
    """
    Test a community admin reviewing an application.
    """

    def setUp(self):
        super().setUp()
        self.application1 = models.CommunityApplication.objects.create(
            gamer=self.gamer3,
            message="Notice me, Senpai!",
            community=self.community1,
            status="review",
        )
        self.application2 = models.CommunityApplication.objects.create(
            gamer=self.gamer2,
            message="I want to play!",
            community=self.community1,
            status="new",
        )
        self.view_str = "gamer_profiles:community-applicant-detail"
        self.url_kwargs = {"community": self.community1.slug}

    def test_login_required(self):
        self.assertLoginRequired(
            self.view_str, application=self.application1.pk, **self.url_kwargs
        )

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, application=self.application1.pk, **self.url_kwargs)
            self.response_403()
            self.get(self.view_str, application=self.application2.pk, **self.url_kwargs)
            self.response_403()

    def test_authorized_can_only_see_submitted(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, application=self.application2.pk, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(
                self.view_str, application=self.application1.pk, **self.url_kwargs
            )


class ApproveApplicationTest(AbstractViewTest):
    """
    Approve view for community admins.
    """

    def setUp(self):
        super().setUp()
        self.application1 = models.CommunityApplication.objects.create(
            gamer=self.gamer3,
            message="Notice me, Senpai!",
            community=self.community1,
            status="review",
        )
        self.application2 = models.CommunityApplication.objects.create(
            gamer=self.gamer2,
            message="I want to play!",
            community=self.community1,
            status="new",
        )
        self.view_str = "gamer_profiles:community-applicant-approve"
        self.valid_url_kwargs = {
            "community": self.community1.slug,
            "application": self.application1.pk,
        }
        self.invalid_url_kwargs = {
            "community": self.community1.slug,
            "application": self.application2.pk,
        }

    def test_login_required(self):
        self.get(self.view_str, **self.valid_url_kwargs)
        self.response_405()
        assert (
            models.CommunityApplication.objects.get(pk=self.application1.pk).status
            == "review"
        )
        self.post(self.view_str, **self.valid_url_kwargs)
        self.response_302()
        assert "login" in self.last_response["location"]
        assert (
            models.CommunityApplication.objects.get(pk=self.application1.pk).status
            == "review"
        )

    def test_unauthorized_users(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.valid_url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.valid_url_kwargs)
            self.response_403()
            assert (
                models.CommunityApplication.objects.get(pk=self.application1.pk).status
                == "review"
            )

    def test_auth_user_with_invalid_target(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.invalid_url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.invalid_url_kwargs)
            self.response_404()
            assert (
                models.CommunityApplication.objects.get(pk=self.application2.pk).status
                == "new"
            )

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.valid_url_kwargs)
            self.response_405()
            assert (
                models.CommunityApplication.objects.get(pk=self.application1.pk).status
                == "review"
            )
            self.post(self.view_str, **self.valid_url_kwargs)
            self.response_302()
            assert (
                models.CommunityApplication.objects.get(pk=self.application1.pk).status
                == "approve"
            )
            assert models.CommunityMembership.objects.get(
                community=self.community1, gamer=self.gamer3
            )


class RejectApplicationTest(ApproveApplicationTest):
    """
    Run the same tests as approval but for rejection.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:community-applicant-reject"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.valid_url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.valid_url_kwargs)
            self.response_302()
            assert (
                models.CommunityApplication.objects.get(pk=self.application1.pk).status
                == "reject"
            )
            with pytest.raises(ObjectDoesNotExist):
                models.CommunityMembership.objects.get(
                    community=self.community1, gamer=self.gamer3
                )


class CommunityKickListTest(AbstractViewTest):
    """
    Test viewing the list of kicked users from a given community.
    """

    def setUp(self):
        super().setUp()
        self.community1.add_member(self.gamer2)
        self.community1.add_member(self.gamer3)
        self.bad_kick = self.community1.kick_user(self.gamer1, self.gamer2, "Bad apple")
        self.good_kick = self.community1.kick_user(
            self.gamer1,
            self.gamer3,
            "Jerk",
            earliest_reapply=timezone.now() + timedelta(days=2),
        )
        self.view_str = "gamer_profiles:community-kick-list"
        self.url_kwargs = {"community": self.community1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            assert self.get_context("kick_list").count() == 1
            assert self.get_context("expired_kicks").count() == 1


class CommunityKickUserTest(AbstractViewTest):
    """
    Test creating a kick record
    """

    def setUp(self):
        super().setUp()
        self.community1.add_member(self.gamer2)
        self.view_str = "gamer_profiles:community-kick-gamer"
        self.url_kwargs = {
            "community": self.community1.slug,
            "gamer": self.gamer2.username,
        }
        self.bad_url_kwargs = {
            "community": self.community1.slug,
            "gamer": self.gamer3.username,
        }
        self.post_data = {
            "reason": "Jerk",
            "end_date": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        }
        self.bad_post_data = {
            "end_date": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.post(self.view_str, data=self.post_data, **self.url_kwargs)
            self.response_403()
            assert (
                models.KickedUser.objects.filter(
                    community=self.community1, kicked_user=self.gamer2
                ).count()
                == 0
            )

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_str, data=self.post_data, **self.bad_url_kwargs)
            self.response_403()
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, data=self.bad_post_data, **self.url_kwargs)
            self.response_200()
            assert (
                models.KickedUser.objects.filter(
                    community=self.community1, kicked_user=self.gamer2
                ).count()
                == 0
            )
            self.post(self.view_str, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.KickedUser.objects.filter(
                    community=self.community1, kicked_user=self.gamer2
                ).count()
                == 1
            )


class CommunityUpdateKickTest(CommunityKickListTest):
    """
    Test attempts to update a kick record.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:community-kick-edit"
        self.url_kwargs = {"community": self.community1.slug, "kick": self.good_kick.pk}
        self.bad_url_kwargs = {
            "community": self.community1.slug,
            "kick": self.bad_kick.pk,
        }
        self.bad_comm_url_kwargs = {
            "community": self.community2.slug,
            "kick": self.good_kick.pk,
        }
        self.bad_post_data = {"gamer": self.gamer2.pk}
        self.good_post_data = {
            "reason": "Posting adult games without CW",
            "end_date": self.good_kick.end_date.strftime("%Y-%m-%d %H:%M"),
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.get(self.view_str, **self.bad_comm_url_kwargs)
            self.response_403()
            self.post(self.view_str, data=self.good_post_data, **self.url_kwargs)
            self.response_403()
            assert models.KickedUser.objects.get(pk=self.good_kick.pk).reason == "Jerk"
            self.post(
                self.view_str, data=self.good_post_data, **self.bad_comm_url_kwargs
            )
            self.response_403()
            assert models.KickedUser.objects.get(pk=self.good_kick.pk).reason == "Jerk"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, data=self.bad_post_data, **self.url_kwargs)
            self.response_200()
            assert models.KickedUser.objects.get(pk=self.good_kick.pk).reason == "Jerk"
            self.post(self.view_str, data=self.good_post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.KickedUser.objects.get(pk=self.good_kick.pk).reason
                == "Posting adult games without CW"
            )

    def test_authorized_user_with_expired_kick(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.bad_url_kwargs)
            self.response_403()
            self.post(self.view_str, data=self.good_post_data, **self.bad_url_kwargs)
            self.response_403()
            assert (
                models.KickedUser.objects.get(pk=self.bad_kick.pk).reason == "Bad apple"
            )


class CommunityKickDeleteTest(CommunityUpdateKickTest):
    """
    Only authorized users should be able to delete a kick.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:community-kick-delete"
        self.url_kwargs = {"community": self.community1.slug, "kick": self.good_kick.pk}
        self.bad_comm_url_kwargs = {
            "community": self.community2.slug,
            "kick": self.good_kick.pk,
        }
        self.good_post_data = {}  # Allows us to reuse methods from CommunityUpdateKickTest

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.KickedUser.objects.get(pk=self.good_kick.pk)

    def test_authorized_user_with_expired_kick(self):
        """
        Not valid for this test.
        """
        pass


class CommunityBanListTest(AbstractViewTest):
    """
    Test viewing the list of banned users from a given community.
    """

    def setUp(self):
        super().setUp()
        self.community1.add_member(self.gamer2)
        self.ban_file = self.community1.ban_user(self.gamer1, self.gamer2, "Jerk")
        self.view_str = "gamer_profiles:community-ban-list"
        self.url_kwargs = {"community": self.community1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            assert self.get_context("ban_list").count() == 1


class CommunityBanUserTest(AbstractViewTest):
    """
    Test creating a ban record
    """

    def setUp(self):
        super().setUp()
        self.community1.add_member(self.gamer2)
        self.view_str = "gamer_profiles:community-ban-gamer"
        self.url_kwargs = {
            "community": self.community1.slug,
            "gamer": self.gamer2.username,
        }
        self.bad_url_kwargs = {
            "community": self.community1.slug,
            "gamer": self.gamer3.username,
        }
        self.post_data = {"reason": "Jerk"}
        self.bad_post_data = {}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.post(self.view_str, data=self.post_data, **self.url_kwargs)
            self.response_403()
            assert (
                models.BannedUser.objects.filter(
                    community=self.community1, banned_user=self.gamer2
                ).count()
                == 0
            )

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_str, data=self.post_data, **self.bad_url_kwargs)
            self.response_403()
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, data=self.bad_post_data, **self.url_kwargs)
            self.response_200()
            assert (
                models.BannedUser.objects.filter(
                    community=self.community1, banned_user=self.gamer2
                ).count()
                == 0
            )
            self.post(self.view_str, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.BannedUser.objects.filter(
                    community=self.community1, banned_user=self.gamer2
                ).count()
                == 1
            )


class CommunityUpdateBanTest(CommunityBanListTest):
    """
    Test attempts to update a ban record.
    """

    def setUp(self):
        super().setUp()
        self.community2.add_member(self.gamer3)
        self.bad_ban_file = self.community2.ban_user(
            self.community2.owner, self.gamer3, "Jerkhole"
        )
        self.view_str = "gamer_profiles:community-ban-edit"
        self.url_kwargs = {"community": self.community1.slug, "ban": self.ban_file.pk}
        self.bad_url_kwargs = {
            "community": self.community1.slug,
            "ban": self.bad_ban_file.pk,
        }
        self.bad_comm_url_kwargs = {
            "community": self.community2.slug,
            "ban": self.ban_file.pk,
        }
        self.bad_post_data = {"gamer": self.gamer2.pk}
        self.good_post_data = {"reason": "Posting adult games without CW"}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.get(self.view_str, **self.bad_comm_url_kwargs)
            self.response_403()
            self.post(self.view_str, data=self.good_post_data, **self.url_kwargs)
            self.response_403()
            assert models.BannedUser.objects.get(pk=self.ban_file.pk).reason == "Jerk"
            self.post(
                self.view_str, data=self.good_post_data, **self.bad_comm_url_kwargs
            )
            self.response_403()
            assert models.BannedUser.objects.get(pk=self.ban_file.pk).reason == "Jerk"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, data=self.bad_post_data, **self.url_kwargs)
            self.response_200()
            assert models.BannedUser.objects.get(pk=self.ban_file.pk).reason == "Jerk"
            self.post(self.view_str, data=self.good_post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.BannedUser.objects.get(pk=self.ban_file.pk).reason
                == "Posting adult games without CW"
            )


class CommunityBanDeleteTest(CommunityUpdateBanTest):
    """
    Only authorized users should be able to delete a ban.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:community-ban-delete"
        self.url_kwargs = {"community": self.community1.slug, "ban": self.ban_file.pk}
        self.bad_comm_url_kwargs = {
            "community": self.community2.slug,
            "ban": self.bad_ban_file.pk,
        }
        self.good_post_data = {}  # Allows us to reuse methods from CommunityUpdateBanTest

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.BannedUser.objects.get(pk=self.ban_file.pk)


class GamerProfileDetailTest(AbstractViewTest):
    """
    Tests for viewing gamer profile.
    """

    def setUp(self):
        super().setUp()
        self.gamer_friend = factories.GamerProfileFactory()
        self.gamer1.friends.add(self.gamer_friend)
        self.gamer3.friends.remove(self.gamer1)
        self.gamer_jerk = factories.GamerProfileFactory()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_jerk)
        self.gamer_public = factories.GamerProfileFactory(private=False)
        self.view_str = "gamer_profiles:profile-detail"
        self.url_kwargs = {"gamer": self.gamer1.username}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_public_profile(self):
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_str, gamer=self.gamer_public.username)

    def test_private_but_stranger(self):
        """
        If a profile is private and the user has no existing connection, it should be redirected
        to an option to friend the player.
        """
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_302()
            assert "friend" in self.last_response["location"]

    def test_public_but_blocked(self):
        with self.login(username=self.gamer_jerk.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_private_same_comm_blocked(self):
        """
        Even if you are in the same community, a blocked user
        cannot see the profile.
        """
        self.community1.add_member(self.gamer_jerk)
        with self.login(username=self.gamer_jerk.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_private_friend_but_blocked(self):
        """
        If someone is a friend, but then subsequently blocked,
        they should be removed from friends and added to blocked users.
        """
        assert self.gamer_friend in self.gamer1.friends.all()
        models.BlockedUser.objects.create(
            blocker=self.gamer1, blockee=self.gamer_friend
        )
        assert self.gamer_friend not in self.gamer1.friends.all()
        with self.login(username=self.gamer_friend.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_private_but_friend(self):
        """
        If profile is private, but user is a friend, show the profile.
        """
        with self.login(username=self.gamer_friend.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)

    def test_private_but_same_comm(self):
        """
        If in the same community, see the profile.
        """
        self.community1.add_member(self.gamer3)
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)


class GamerProfileUpdateTest(AbstractViewTest):
    """
    Test the updating of both user model and gamer profile
    in save view.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:profile-edit"
        self.valid_post = {
            "display_name": "Charles",
            "bio": "Born in the USA",
            "homepage_url": "https://www.google.com",
            "profile-private": 1,
            "profile-rpg_experience": "I dabble",
            "profile-ttg_experience": "A few rounds of Catan",
            "profile-player_status": "searching",
            "profile-one_shots": 1,
            "profile-online_games": 1,
        }
        self.invalid_user_post = {
            "display_name": "Charles",
            "bio": """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras ipsum nibh, tempus et feugiat sit amet, egestas tincidunt tortor. Fusce pellentesque laoreet ultrices. Proin luctus ullamcorper erat, in rhoncus ipsum semper sit amet. Suspendisse felis risus, placerat a semper sed, commodo eu velit. Sed feugiat venenatis ultricies. Vivamus ullamcorper, leo eget mollis mollis, libero nisl pulvinar nisi, non pharetra nulla odio vitae purus. Pellentesque et libero eros, sed tincidunt ligula. Phasellus id metus justo. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Ut mollis tincidunt bibendum.

Pellentesque faucibus, risus eu mattis viverra, tortor tellus lobortis nibh, vel suscipit justo odio euismod mauris. Etiam consectetur, lorem sit amet iaculis rhoncus, nulla sapien dictum erat, id eleifend ligula neque congue sapien. Proin in posuere risus. Nullam porttitor venenatis velit, id malesuada urna egestas eget. Praesent eget turpis vitae elit suscipit luctus et vel lectus. Etiam sapien nulla, imperdiet porta accumsan in, facilisis et lacus. Etiam risus dui, ornare eget fringilla eget, consequat vel odio. Nam diam leo, lacinia sit amet sagittis vel, blandit nec felis. Pellentesque mattis malesuada orci, ac lobortis lacus pellentesque sit amet. Morbi tempus diam eu quam luctus tempor. Mauris pretium, lectus id elementum faucibus, turpis urna dignissim metus, eu viverra nibh purus id nisi. Nunc id nunc quam. Suspendisse vitae lacus nisl, vel placerat libero. Donec dui enim, congue ac dictum id, ullamcorper sit amet elit. Maecenas nunc purus, viverra id placerat vitae, mollis a orci. Curabitur mi augue, sagittis ut eleifend ut, tincidunt ut dui. Etiam sed neque mauris, sed sagittis augue. Quisque eu tellus mi, non vehicula sem.

Vestibulum aliquam tincidunt sodales. Cras gravida metus sollicitudin odio consectetur quis aliquam ligula volutpat. Sed ac urna lacus, a iaculis tortor. Praesent nunc purus, egestas non auctor id, suscipit vitae sem. Ut congue libero eget est condimentum ac vestibulum sem vestibulum. Quisque vitae placerat lacus. Nam porta hendrerit pretium. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum luctus ipsum quis ante malesuada porttitor. Phasellus sagittis pulvinar ante vel ultricies. Curabitur ut pulvinar elit. Proin odio dui, scelerisque vel blandit quis, commodo nec ligula. Maecenas ut imperdiet neque. Suspendisse ligula nisi, aliquam vitae dignissim ut, consectetur sit amet nibh. Nunc euismod tempor commodo. Morbi eget enim augue. Aliquam tempus, velit a fringilla fermentum, tellus dolor hendrerit mauris, at fermentum nibh nisi vulputate velit. Sed orci eros, porta quis sodales at, malesuada id tortor. Quisque dictum orci a mauris dictum gravida. Morbi nec nisi sollicitudin eros rhoncus tincidunt a in lacus.

Duis hendrerit nibh vel neque rutrum quis rhoncus lorem porta. Phasellus magna ipsum, laoreet vitae malesuada eu, ultricies et neque. Phasellus auctor tincidunt lectus, vitae interdum tellus gravida eu. Donec tempus tellus a metus blandit blandit. Praesent placerat faucibus auctor. Duis non gravida enim. Fusce in sem magna. Vivamus luctus fermentum bibendum. Morbi orci libero, accumsan ac feugiat nec, mattis id dui. Morbi malesuada varius vulputate. Morbi sagittis ultrices tellus vel lobortis. Suspendisse a lorem ac tellus porttitor auctor. Maecenas imperdiet faucibus cursus. Sed vestibulum leo in leo tincidunt tristique. Praesent eu elit augue.

Nunc auctor rutrum ligula ut consectetur. Integer eget lorem elementum diam hendrerit ullamcorper sit amet sodales odio. Phasellus tellus arcu, tempor et consequat eu, malesuada in odio. Aliquam mollis, ipsum et tristique euismod, augue urna porttitor mauris, quis iaculis ipsum risus ac erat. Phasellus urna nisi, pharetra vitae semper sed, pretium non odio. Cras diam justo, mollis a vulputate non, condimentum in ligula. Proin vulputate tincidunt accumsan. Duis urna justo, dapibus vitae bibendum ac, facilisis at purus. Phasellus euismod adipiscing nunc eget pulvinar. Nullam dui leo, malesuada sed lobortis eget, rutrum vel justo. Phasellus ipsum nunc, aliquet eu aliquet eget, blandit id est. Maecenas eu est massa, sit amet tempus nisl. In vel nulla vitae turpis blandit ultricies. Aenean ornare justo at eros auctor nec interdum neque euismod. Aliquam laoreet, neque ac varius rutrum, purus purus consequat leo, nec pretium dui justo a nulla. Morbi suscipit euismod odio quis viverra. Integer commodo orci vehicula nisi varius euismod. Aenean egestas nulla sed ligula tincidunt id posuere dolor malesuada. """,
            "homepage_url": "https://www.google.com",
            "profile-private": 1,
            "profile-rpg_experience": "I dabble",
            "profile-ttg_experience": "A few rounds of Catan",
            "profile-player_status": "searching",
            "profile-one_shots": 1,
            "profile-online_games": 1,
        }
        self.invalid_profile_post = {
            "display_name": "Charles",
            "bio": "Born in the USA",
            "homepage_url": "https://www.google.com",
            "profile-private": 1,
            "profile-rpg_experience": "I dabble",
            "profile-ttg_experience": "A few rounds of Catan",
            "profile-player_status": "ooga shakka",
            "profile-one_shots": 1,
            "profile-online_games": 1,
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_str)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str)

    def test_invalid_user_form(self):
        orig_bio = self.gamer1.user.bio
        with self.login(username=self.gamer1.username):
            self.post(self.view_str, data=self.invalid_user_post)
            self.response_200()
            assert (
                type(self.gamer1.user).objects.get(pk=self.gamer1.user.pk).bio
                == orig_bio
            )

    def test_invalid_profile_form(self):
        orig_status = self.gamer1.player_status
        with self.login(username=self.gamer1.username):
            self.post(self.view_str, data=self.invalid_profile_post)
            self.response_200()
            assert (
                models.GamerProfile.objects.get(pk=self.gamer1.pk).player_status
                == orig_status
            )

    def test_valid_form(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_str, data=self.valid_post)
            # form = self.get_context('form')
            # if form.errors:
            #     print(form.errors.as_data())
            # profile_form = self.get_context('profile_form')
            # if profile_form.errors:
            #     print(profile_form.errors.as_data())
            self.response_302()
            assert (
                type(self.gamer1.user).objects.get(pk=self.gamer1.user.pk).display_name
                == "Charles"
            )
            assert (
                models.GamerProfile.objects.get(pk=self.gamer1.pk).player_status
                == "searching"
            )


class GamerFriendRequestTest(AbstractViewTest):
    """
    Tests the view for submitting friend requests.
    """

    def setUp(self):
        super().setUp()
        self.gamer_friend = factories.GamerProfileFactory()
        self.gamer1.friends.add(self.gamer_friend)
        self.gamer3.friends.remove(self.gamer1)
        self.gamer_jerk = factories.GamerProfileFactory()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_jerk)
        self.gamer_public = factories.GamerProfileFactory(private=False)
        self.view_str = "gamer_profiles:gamer-friend"
        self.url_kwargs = {"gamer": self.gamer1.username}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_blocked_user(self):
        with self.login(username=self.gamer_jerk.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_already_friends(self):
        with self.login(username=self.gamer_friend.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_302()
            current_requests = models.GamerFriendRequest.objects.filter(
                requestor=self.gamer_friend, recipient=self.gamer1
            ).count()
            assert current_requests == 0
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert (
                current_requests
                == models.GamerFriendRequest.objects.filter(
                    requestor=self.gamer_friend, recipient=self.gamer1
                ).count()
            )

    def reverse_request_already_received(self):
        assert self.gamer3 not in self.gamer1.friends.all()
        test_request = models.GamerFriendRequest.objects.create(
            requestor=self.gamer1, recipient=self.gamer3, status="new"
        )
        with self.login(username=self.gamer3.username):
            self.post(self.view_str, **self.url_kwargs)
            test_request.refresh_from_db()
            assert test_request.status == "approve"
            assert self.gamer3 in self.gamer1.friends.all()

    def test_authorized_user(self):
        with self.login(username=self.gamer3.username):
            with transaction.atomic():
                with pytest.raises(ObjectDoesNotExist):
                    models.GamerFriendRequest.objects.get(
                        requestor=self.gamer3, recipient=self.gamer1
                    )
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert models.GamerFriendRequest.objects.get(
                requestor=self.gamer3, recipient=self.gamer1
            )

    def test_request_already_queued(self):
        models.GamerFriendRequest.objects.create(
            requestor=self.gamer3, recipient=self.gamer1, status="new"
        )
        assert (
            models.GamerFriendRequest.objects.filter(
                requestor=self.gamer3, recipient=self.gamer1
            ).count()
            == 1
        )
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.assertInContext("pending_request")
            self.post(self.view_str, **self.url_kwargs)
            assert (
                models.GamerFriendRequest.objects.filter(
                    requestor=self.gamer3, recipient=self.gamer1
                ).count()
                == 1
            )


class GamerFriendRequestWithdrawTest(AbstractViewTest):
    """
    Test that only the creator of a friend request can delete it.
    """

    def setUp(self):
        super().setUp()
        self.gamer_friend = factories.GamerProfileFactory()
        self.gamer1.friends.add(self.gamer_friend)
        self.gamer3.friends.remove(self.gamer1)
        self.request_obj = models.GamerFriendRequest.objects.create(
            requestor=self.gamer3, recipient=self.gamer1, status="new"
        )
        self.gamer_jerk = factories.GamerProfileFactory()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_jerk)
        self.gamer_public = factories.GamerProfileFactory(private=False)
        self.view_str = "gamer_profiles:gamer-friend-request-delete"
        self.url_kwargs = {"friend_request": self.request_obj.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.GamerFriendRequest.objects.get(pk=self.request_obj.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            with pytest.raises(ObjectDoesNotExist):
                models.GamerFriendRequest.objects.get(pk=self.request_obj.pk)


class GamerFriendRequestApproveTest(AbstractViewTest):
    """
    Test request approvals.
    """

    def setUp(self):
        super().setUp()
        self.new_frand = factories.GamerProfileFactory()
        self.friend_request = models.GamerFriendRequest.objects.create(
            requestor=self.new_frand, recipient=self.gamer1, status="new"
        )
        self.view_str = "gamer_profiles:gamer-friend-request-approve"
        self.url_kwargs = {"friend_request": self.friend_request.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert (
                models.GamerFriendRequest.objects.get(pk=self.friend_request.pk).status
                == "new"
            )

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert (
                models.GamerFriendRequest.objects.get(pk=self.friend_request.pk).status
                != "new"
            )
            assert self.new_frand in self.gamer1.friends.all()


class GamerFriendRequestDenyTest(GamerFriendRequestApproveTest):
    """
    Test request denials
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:gamer-friend-request-reject"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert (
                models.GamerFriendRequest.objects.get(pk=self.friend_request.pk).status
                != "new"
            )
            assert self.new_frand not in self.gamer1.friends.all()


class GamerFriendRequestListTest(AbstractViewTest):
    """
    View requests.
    """

    def setUp(self):
        super().setUp()
        self.new_frand = factories.GamerProfileFactory()
        self.new_frand2 = factories.GamerProfileFactory()
        self.new_frand3 = factories.GamerProfileFactory()
        self.friend_request = models.GamerFriendRequest.objects.create(
            requestor=self.new_frand, recipient=self.gamer1, status="new"
        )
        self.friend_request2 = models.GamerFriendRequest.objects.create(
            requestor=self.new_frand2, recipient=self.gamer1, status="new"
        )
        self.sent_request = models.GamerFriendRequest.objects.create(
            requestor=self.gamer1, recipient=self.gamer2, status="new"
        )
        self.extra_request = models.GamerFriendRequest.objects.create(
            requestor=self.gamer1, recipient=self.new_frand3, status="new"
        )
        self.extra_request.accept()
        self.view_str = "gamer_profiles:my-gamer-friend-requests"

    def test_login_required(self):
        self.assertLoginRequired(self.view_str)

    def test_authenticated_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str)
            assert self.get_context("pending_requests").count() == 2
            assert self.get_context("sent_requests").count() == 1
            self.friend_request.accept()
            self.assertGoodView(self.view_str)
            assert self.get_context("pending_requests").count() == 1


class MuteGamerTest(AbstractViewTest):
    """
    A post only method to mute a gamer. If arg 'next' is provided,
    will redirect to that, otherwise goes to target's profile page.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:mute-gamer"
        self.url_kwargs = {
            "gamer": self.gamer3.username,
            "next": reverse("gamer_profiles:my-community-list"),
        }

    def test_login_required(self):
        self.get(self.view_str, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_auth_user(self):
        assert (
            models.MutedUser.objects.filter(
                muter=self.gamer1, mutee=self.gamer3
            ).count()
            == 0
        )
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert "communities" in self.last_response["location"]
            assert (
                models.MutedUser.objects.filter(
                    muter=self.gamer1, mutee=self.gamer3
                ).count()
                == 1
            )


class RemoveMuteTest(AbstractViewTest):
    """
    Only the person who created a given mute record can remove it.
    """

    def setUp(self):
        super().setUp()
        self.mute_record = models.MutedUser.objects.create(
            muter=self.gamer1, mutee=self.gamer3
        )
        self.view_str = "gamer_profiles:unmute-gamer"
        self.url_kwargs = {
            "mute": self.mute_record.pk,
            "next": reverse(
                "gamer_profiles:profile-detail",
                kwargs={"gamer": self.mute_record.mutee.pk},
            ),
        }
        print(reverse(self.view_str, kwargs=self.url_kwargs))

    def test_login_required(self):
        self.get(self.view_str, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.MutedUser.objects.get(pk=self.mute_record.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert "profile" in self.last_response["location"]
            with pytest.raises(ObjectDoesNotExist):
                models.MutedUser.objects.get(pk=self.mute_record.pk)


class BlockGamerTest(AbstractViewTest):
    """
    A post only method to block a gamer. If arg 'next' is provided,
    will redirect to that, otherwise goes to target's profile page.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:block-gamer"
        self.url_kwargs = {
            "gamer": self.gamer3.username,
            "next": reverse("gamer_profiles:my-community-list"),
        }

    def test_login_required(self):
        self.get(self.view_str, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_auth_user(self):
        assert (
            models.BlockedUser.objects.filter(
                blocker=self.gamer1, blockee=self.gamer3
            ).count()
            == 0
        )
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert "communities" in self.last_response["location"]
            assert (
                models.BlockedUser.objects.filter(
                    blocker=self.gamer1, blockee=self.gamer3
                ).count()
                == 1
            )


class RemoveBlockTest(AbstractViewTest):
    """
    Only the person who created a given block record can remove it.
    """

    def setUp(self):
        super().setUp()
        self.block_record = models.BlockedUser.objects.create(
            blocker=self.gamer1, blockee=self.gamer3
        )
        self.view_str = "gamer_profiles:unblock-gamer"
        self.url_kwargs = {
            "block": self.block_record.pk,
            "next": reverse(
                "gamer_profiles:profile-detail",
                kwargs={"gamer": self.block_record.blockee.pk},
            ),
        }
        print(reverse(self.view_str, kwargs=self.url_kwargs))

    def test_login_required(self):
        self.get(self.view_str, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.BlockedUser.objects.get(pk=self.block_record.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert "profile" in self.last_response["location"]
            with pytest.raises(ObjectDoesNotExist):
                models.BlockedUser.objects.get(pk=self.block_record.pk)


class CreateGamerNoteTest(AbstractViewTest):
    """
    Test create view for gamer notes.
    """

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:add-gamer-note"
        self.url_kwargs = {"gamer": self.gamer3.username}
        self.post_url_kwargs = {
            "gamer": self.gamer3.username,
            "data": {"title": "Test note", "body": "Hi **there**!"},
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            assert models.GamerNote.objects.filter(gamer=self.gamer3).count() == 0
            self.assertGoodView(self.view_str, **self.url_kwargs)
            assert models.GamerNote.objects.filter(gamer=self.gamer3).count() == 0
            self.post(self.view_str, **self.post_url_kwargs)
            self.response_302()
            assert models.GamerNote.objects.filter(gamer=self.gamer3).count() == 1


class UpdateGamerNoteTest(AbstractViewTest):
    """
    Test updating a gamer note.
    """

    def setUp(self):
        super().setUp()
        self.gn = models.GamerNote.objects.create(
            author=self.gamer1,
            gamer=self.gamer3,
            title="Test Note",
            body="Hi **there**!",
        )
        self.view_str = "gamer_profiles:edit-gamernote"
        self.url_kwargs = {"gamernote": self.gn.pk}
        self.post_url_kwargs = {
            "gamernote": self.gn.pk,
            "data": {
                "title": "New Title",
                "body": "Something [new](https://www.google.com)",
            },
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.post(self.view_str, **self.post_url_kwargs)
            self.response_403()
            assert models.GamerNote.objects.get(pk=self.gn.pk).title == "Test Note"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            # test invalid form
            self.post(self.view_str, **self.url_kwargs)
            self.response_200()  # Form errors
            assert models.GamerNote.objects.get(pk=self.gn.pk).title == "Test Note"
            self.post(self.view_str, **self.post_url_kwargs)
            self.response_302()
            assert models.GamerNote.objects.get(pk=self.gn.pk).title == "New Title"


class DeleteGamerNoteTest(AbstractViewTest):
    """
    Test deleting a gamer note.
    """

    def setUp(self):
        super().setUp()
        self.gn = models.GamerNote.objects.create(
            author=self.gamer1,
            gamer=self.gamer3,
            title="Test Note",
            body="Hi **there**!",
        )
        self.view_str = "gamer_profiles:delete-gamernote"
        self.url_kwargs = {"gamernote": self.gn.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.GamerNote.objects.get(pk=self.gn.pk)
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.GamerNote.objects.get(pk=self.gn.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.GamerNote.objects.get(pk=self.gn.pk)
