import pytest
from datetime import timedelta
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
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
            self.response_403()
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            assert current_apps == 0
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
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
        with self.login(username=self.gamer3.user.username):
            current_apps = models.CommunityApplication.objects.filter(
                community=self.community1
            ).count()
            self.get("gamer_profiles:community-apply", community=self.community1.pk)
            self.response_403()
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
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

    def test_normal_user_submit(self):
        with self.login(username=self.gamer3.user.username):
            submit_data = self.apply_data
            submit_data["submit_app"] = ""
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
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
        with self.login(username=self.gamer2.user.username):
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

    def test_owner_submit(self):
        with self.login(username=self.gamer3.user.username):
            submit_data = self.update_data
            submit_data["submit_app"] = ""
            self.post(
                "gamer_profiles:community-apply",
                community=self.community1.pk,
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
        with self.login(username=self.gamer2.user.username):
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
        with self.login(username=self.gamer3.user.username):
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
        self.url_kwargs = {"community": self.community1.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
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
        self.url_kwargs = {"community": self.community1.pk}

    def test_login_required(self):
        self.assertLoginRequired(
            self.view_str, application=self.application1.pk, **self.url_kwargs
        )

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.user.username):
            self.get(self.view_str, application=self.application1.pk, **self.url_kwargs)
            self.response_403()
            self.get(self.view_str, application=self.application2.pk, **self.url_kwargs)
            self.response_403()

    def test_authorized_can_only_see_submitted(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, application=self.application2.pk, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView(
                self.view_str, application=self.application1.pk, **self.url_kwargs
            )


class ApproveApplicationTest(AbstractViewTest):
    '''
    Approve view for community admins.
    '''

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
        self.valid_url_kwargs = {"community": self.community1.pk, "application": self.application1.pk}
        self.invalid_url_kwargs = {"community": self.community1.pk, "application": self.application2.pk}

    def test_login_required(self):
        self.get(self.view_str, **self.valid_url_kwargs)
        self.response_405()
        assert models.CommunityApplication.objects.get(pk=self.application1.pk).status == "review"
        self.post(self.view_str, **self.valid_url_kwargs)
        self.response_302()
        assert 'login' in self.last_response['location']
        assert models.CommunityApplication.objects.get(pk=self.application1.pk).status == "review"

    def test_unauthorized_users(self):
        with self.login(username=self.gamer2.user.username):
            self.get(self.view_str, **self.valid_url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.valid_url_kwargs)
            self.response_403()
            assert models.CommunityApplication.objects.get(pk=self.application1.pk).status == "review"

    def test_auth_user_with_invalid_target(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, **self.invalid_url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.invalid_url_kwargs)
            self.response_404()
            assert models.CommunityApplication.objects.get(pk=self.application2.pk).status == "new"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, **self.valid_url_kwargs)
            self.response_405()
            assert models.CommunityApplication.objects.get(pk=self.application1.pk).status == "review"
            self.post(self.view_str, **self.valid_url_kwargs)
            self.response_302()
            assert models.CommunityApplication.objects.get(pk=self.application1.pk).status == "approve"
            assert models.CommunityMembership.objects.get(community=self.community1, gamer=self.gamer3)


class RejectApplicationTest(ApproveApplicationTest):
    '''
    Run the same tests as approval but for rejection.
    '''

    def setUp(self):
        super().setUp()
        self.view_str = "gamer_profiles:community-applicant-reject"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, **self.valid_url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.valid_url_kwargs)
            self.response_302()
            assert models.CommunityApplication.objects.get(pk=self.application1.pk).status == "reject"
            with pytest.raises(ObjectDoesNotExist):
                models.CommunityMembership.objects.get(community=self.community1, gamer=self.gamer3)


class GamerProfileDetailTest(AbstractViewTest):
    '''
    Tests for viewing gamer profile.
    '''

    def setUp(self):
        super().setUp()
        self.gamer_friend = factories.GamerProfileFactory()
        self.gamer1.friends.add(self.gamer_friend)
        self.gamer3.friends.remove(self.gamer1)
        self.gamer_jerk = factories.GamerProfileFactory()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_jerk)
        self.gamer_public = factories.GamerProfileFactory(private=False)
        self.view_str = 'gamer_profiles:profile-detail'
        self.url_kwargs = {'gamer': self.gamer1.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_public_profile(self):
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(self.view_str, gamer=self.gamer_public.pk)

    def test_private_but_stranger(self):
        '''
        If a profile is private and the user has no existing connection, it should be redirected
        to an option to friend the player.
        '''
        with self.login(username=self.gamer3.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_302()
            assert 'friend' in self.last_response['location']

    def test_public_but_blocked(self):
        with self.login(username=self.gamer_jerk.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_private_same_comm_blocked(self):
        '''
        Even if you are in the same community, a blocked user
        cannot see the profile.
        '''
        self.community1.add_member(self.gamer_jerk)
        with self.login(username=self.gamer_jerk.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_private_friend_but_blocked(self):
        '''
        If someone is a friend, but then subsequently blocked,
        they should be removed from friends and added to blocked users.
        '''
        assert self.gamer_friend in self.gamer1.friends.all()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_friend)
        assert self.gamer_friend not in self.gamer1.friends.all()
        with self.login(username=self.gamer_friend.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_private_but_friend(self):
        '''
        If profile is private, but user is a friend, show the profile.
        '''
        with self.login(username=self.gamer_friend.user.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)

    def test_private_but_same_comm(self):
        '''
        If in the same community, see the profile.
        '''
        self.community1.add_member(self.gamer3)
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)


class GamerFriendRequestTest(AbstractViewTest):
    '''
    Tests the view for submitting friend requests.
    '''

    def setUp(self):
        super().setUp()
        self.gamer_friend = factories.GamerProfileFactory()
        self.gamer1.friends.add(self.gamer_friend)
        self.gamer3.friends.remove(self.gamer1)
        self.gamer_jerk = factories.GamerProfileFactory()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_jerk)
        self.gamer_public = factories.GamerProfileFactory(private=False)
        self.view_str = 'gamer_profiles:gamer-friend'
        self.url_kwargs = {'gamer': self.gamer1.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_blocked_user(self):
        with self.login(username=self.gamer_jerk.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_403()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()

    def test_already_friends(self):
        with self.login(username=self.gamer_friend.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_302()
            current_requests = models.GamerFriendRequest.objects.filter(requestor=self.gamer_friend, recipient=self.gamer1).count()
            assert current_requests == 0
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert current_requests == models.GamerFriendRequest.objects.filter(requestor=self.gamer_friend, recipient=self.gamer1).count()

    def reverse_request_already_received(self):
        assert self.gamer3 not in self.gamer1.friends.all()
        test_request = models.GamerFriendRequest.objects.create(requestor=self.gamer1, recipient=self.gamer3, status='new')
        with self.login(username=self.gamer3.user.username):
            self.post(self.view_str, **self.url_kwargs)
            test_request.refresh_from_db()
            assert test_request.status == 'approve'
            assert self.gamer3 in self.gamer1.friends.all()

    def test_authorized_user(self):
        with self.login(username=self.gamer3.user.username):
            with transaction.atomic():
                with pytest.raises(ObjectDoesNotExist):
                    models.GamerFriendRequest.objects.get(requestor=self.gamer3, recipient=self.gamer1)
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert models.GamerFriendRequest.objects.get(requestor=self.gamer3, recipient=self.gamer1)

    def test_request_already_queued(self):
        models.GamerFriendRequest.objects.create(requestor=self.gamer3, recipient=self.gamer1, status='new')
        assert models.GamerFriendRequest.objects.filter(requestor=self.gamer3, recipient=self.gamer1).count() == 1
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(self.view_str, **self.url_kwargs)
            self.assertInContext('pending_request')
            self.post(self.view_str, **self.url_kwargs)
            assert models.GamerFriendRequest.objects.filter(requestor=self.gamer3, recipient=self.gamer1).count() == 1


class GamerFriendRequestWithdrawTest(AbstractViewTest):
    '''
    Test that only the creator of a friend request can delete it.
    '''

    def setUp(self):
        super().setUp()
        self.gamer_friend = factories.GamerProfileFactory()
        self.gamer1.friends.add(self.gamer_friend)
        self.gamer3.friends.remove(self.gamer1)
        self.request_obj = models.GamerFriendRequest.objects.create(requestor=self.gamer3, recipient=self.gamer1, status='new')
        self.gamer_jerk = factories.GamerProfileFactory()
        models.BlockedUser.objects.create(blocker=self.gamer1, blockee=self.gamer_jerk)
        self.gamer_public = factories.GamerProfileFactory(private=False)
        self.view_str = 'gamer_profiles:gamer-friend-request-delete'
        self.url_kwargs = {'friend_request': self.request_obj.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.GamerFriendRequest.objects.get(pk=self.request_obj.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer3.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            with pytest.raises(ObjectDoesNotExist):
                models.GamerFriendRequest.objects.get(pk=self.request_obj.pk)


class GamerFriendRequestApproveTest(AbstractViewTest):
    '''
    Test request approvals.
    '''

    def setUp(self):
        super().setUp()
        self.new_frand = factories.GamerProfileFactory()
        self.friend_request = models.GamerFriendRequest.objects.create(requestor=self.new_frand, recipient=self.gamer1, status='new')
        self.view_str = 'gamer_profiles:gamer-friend-request-approve'
        self.url_kwargs = {'friend_request': self.friend_request.pk}

    def test_login_required(self):
        self.assertLoginRequired(self.view_str, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_403()
            assert models.GamerFriendRequest.objects.get(pk=self.friend_request.pk).status == "new"

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert models.GamerFriendRequest.objects.get(pk=self.friend_request.pk).status != "new"
            assert self.new_frand in self.gamer1.friends.all()


class GamerFriendRequestDenyTest(GamerFriendRequestApproveTest):
    '''
    Test request denials
    '''

    def setUp(self):
        super().setUp()
        self.view_str = 'gamer_profiles:gamer-friend-request-reject'

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert models.GamerFriendRequest.objects.get(pk=self.friend_request.pk).status != 'new'
            assert self.new_frand not in self.gamer1.friends.all()


class GamerFriendRequestListTest(AbstractViewTest):
    '''
    View requests.
    '''

    def setUp(self):
        super().setUp()
        self.new_frand = factories.GamerProfileFactory()
        self.new_frand2 = factories.GamerProfileFactory()
        self.new_frand3 = factories.GamerProfileFactory()
        self.friend_request = models.GamerFriendRequest.objects.create(requestor=self.new_frand, recipient=self.gamer1, status='new')
        self.friend_request2 = models.GamerFriendRequest.objects.create(requestor=self.new_frand2, recipient=self.gamer1, status='new')
        self.sent_request = models.GamerFriendRequest.objects.create(requestor=self.gamer1, recipient=self.gamer2, status='new')
        self.extra_request = models.GamerFriendRequest.objects.create(requestor=self.gamer1, recipient=self.new_frand3, status='new')
        self.extra_request.accept()
        self.view_str = 'gamer_profiles:my-gamer-friend-requests'

    def test_login_required(self):
        self.assertLoginRequired(self.view_str)

    def test_authenticated_user(self):
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView(self.view_str)
            assert self.get_context('pending_requests').count() == 2
            assert self.get_context('sent_requests').count() == 1
            self.friend_request.accept()
            self.assertGoodView(self.view_str)
            assert self.get_context('pending_requests').count() == 1


class MuteGamerTest(AbstractViewTest):
    '''
    A post only method to mute a gamer. If arg 'next' is provided,
    will redirect to that, otherwise goes to target's profile page.
    '''

    def setUp(self):
        super().setUp()
        self.view_str = 'gamer_profiles:mute-gamer'
        self.url_kwargs = {'gamer': self.gamer3.pk, 'next': reverse('gamer_profiles:my-community-list')}

    def test_login_required(self):
        self.get(self.view_str, **self.url_kwargs)
        self.response_302()
        assert 'accounts/login' in self.last_response['location']

    def test_auth_user(self):
        assert models.MutedUser.objects.filter(muter=self.gamer1, mutee=self.gamer3).count() == 0
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, **self.url_kwargs)
            self.response_405()
            self.post(self.view_str, **self.url_kwargs)
            self.response_302()
            assert 'communities' in self.last_response['location']
            assert models.MutedUser.objects.filter(muter=self.gamer1, mutee=self.gamer3).count() == 1


class RemoveMuteTest(AbstractViewTest):
    '''
    Only the person who created a given mute record can remove it.
    '''

    def setUp(self):
        super().setUp()
        self.mute_record = models.MutedUser.objects.create(muter=self.gamer1, mutee=self.gamer3)
        self.view_str = 'gamer_profiles:unmute-gamer'
        self.url_kwargs = {'mute': self.mute_record.pk, 'next': reverse('gamer_profiles:profile-detail', kwargs={'gamer': self.mute_record.mutee.pk})}

    def test_login_required(self):
        self.get(self.view_str, self.url_kwargs)
        self.response_302()
        assert 'accounts/login' in self.last_response['location']

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.user.username):
            self.get(self.view_str, self.url_kwargs)
            self.response_405()
            self.post(self.view_str, self.url_kwargs)
            self.response_403()
            assert models.MutedUser.objects.get(pk=self.mute_record.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.user.username):
            self.get(self.view_str, self.url_kwargs)
            self.response_405()
            self.post(self.view_str, self.url_kwargs)
            self.response_302()
            assert 'profile' in self.last_response['location']
            with pytest.raises(ObjectDoesNotExist):
                models.MutedUser.objects.get(pk=self.mute_record.pk)
