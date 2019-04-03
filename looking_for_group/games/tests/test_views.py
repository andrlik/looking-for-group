import urllib
from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_delete
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from factory.django import mute_signals
from test_plus import APITestCase, TestCase
from test_plus.test import BaseTestCase

from .. import models
from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory
from ...invites.models import Invite
from ..utils import mkfirstOfmonth, mkLastOfMonth


class AbstractViewTestCase(object):
    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.gamer4 = GamerProfileFactory()
        self.comm1 = GamerCommunityFactory(owner=self.gamer1)
        self.comm2 = GamerCommunityFactory(owner=self.gamer2)
        self.comm1.add_member(self.gamer3)
        self.gamer1.friends.add(self.gamer4)
        self.gp1 = models.GamePosting.objects.create(
            game_type="campaign",
            title="A spoopy campaign",
            gm=self.gamer4,
            privacy_level="public",
            min_players=1,
            max_players=5,
            game_frequency="weekly",
            session_length=2.5,
            game_description="We will roll dice!",
        )
        self.gp4 = models.GamePosting.objects.create(
            game_type="campaign",
            title="A spoopy campaign",
            gm=self.gamer4,
            privacy_level="private",
            min_players=1,
            max_players=5,
            game_frequency="weekly",
            session_length=2.5,
            game_description="We will roll more dice.",
        )
        self.gp2 = models.GamePosting.objects.create(
            game_type="campaign",
            title="A community campaign",
            gm=self.gamer1,
            privacy_level="community",
            min_players=1,
            max_players=5,
            game_frequency="weekly",
            session_length=2.5,
            game_description="we will pretend to be elves",
        )
        self.gp2.communities.add(self.comm1)
        self.gp3 = models.GamePosting.objects.create(
            game_type="campaign",
            title="A private game",
            gm=self.gamer3,
            privacy_level="private",
            min_players=1,
            max_players=5,
            game_frequency="weekly",
            session_length=2.5,
            game_description="We will eat snacks.",
        )
        self.gp5 = models.GamePosting.objects.create(
            game_type="campaign",
            status="cancel",
            title="A spoopy campaign",
            gm=self.gamer4,
            privacy_level="public",
            min_players=1,
            max_players=5,
            game_frequency="weekly",
            session_length=2.5,
            game_description="We are fond of rolling dice.",
        )

    def tearDown(self):
        ContentType.objects.clear_cache()
        super().tearDown()


class AbstractViewTestCaseNoSignals(AbstractViewTestCase, TestCase):
    pass


class AbstractAPITestCase(AbstractViewTestCase, APITestCase):
    pass


class AbstractTestCaseSignals(TransactionTestCase, BaseTestCase):
    """
    Since we can't use test_plus here, we duplicate the API here for the thngs we use.
    """

    user_factory = None

    def __init__(self, *args, **kwargs):
        self.last_response = None
        super().__init__(*args, **kwargs)


class AbstractViewTestCaseSignals(AbstractViewTestCase, AbstractTestCaseSignals):
    pass


class GamePostingListTest(AbstractViewTestCaseNoSignals):
    """
    Test the game posting list view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_list"

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_visability(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name)
            games = self.get_context("game_list")
            assert games.count() == 2
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name)
            games = self.get_context("game_list")
            assert games.count() == 1
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_name)
            games = self.get_context("game_list")
            assert games.count() == 3
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name)
            games = self.get_context("game_list")
            assert games.count() == 3


class MyGameListTest(AbstractViewTestCaseSignals):
    """
    Test the view for a gamer's games.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:my_game_list"
        self.player1 = models.Player.objects.create(game=self.gp2, gamer=self.gamer4)
        self.player2 = models.Player.objects.create(game=self.gp3, gamer=self.gamer4)
        self.gp4.status = "closed"
        self.gp4.save()

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_valid_user(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name)
            assert len(self.get_context("active_game_list")) == 3
            assert len(self.get_context("completed_game_list")) == 2


class GamePostingCreateTest(AbstractViewTestCaseNoSignals):
    """
    Test creation of a game posting.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_create"
        self.valid_post_data = {
            "title": "A Valid Campaign",
            "status": "open",
            "game_type": "campaign",
            "privacy_level": "private",
            "min_players": 1,
            "max_players": 3,
            "game_description": "We like pie.",
            "session_length": 2.5,
            "game_frequency": "weekly",
            "communities": [self.comm1.pk],
        }

    def test_login_required(self):
        previous_count = models.GamePosting.objects.count()
        self.assertLoginRequired(self.view_name)
        self.post(self.view_name, data=self.valid_post_data)
        assert "accounts/login" in self.last_response["location"]
        assert previous_count == models.GamePosting.objects.count()

    def test_form_load(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name)

    def test_invalid_community_submission(self):
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.valid_post_data)
            self.response_200()
            assert len(self.get_context("form").errors) > 0

    def test_valid_submission(self):
        previous_count = models.GamePosting.objects.count()
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.valid_post_data)
            self.response_302()
            assert models.GamePosting.objects.count() - previous_count == 1


class GamePostingDetailTest(AbstractViewTestCaseNoSignals):
    """
    Test for game posting detail view and permissions.
    Note that a private link **can** be used to view it,
    but should get the apply view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_detail"
        self.gamer3.block(self.gamer1)

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, gameid=self.gp2.slug)

    def test_view_load(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, gameid=self.gp2.slug)

    def test_applicant_view(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, gameid=self.gp2.slug)
            self.response_302()
            assert "/apply/" in self.last_response["location"]


class GamePostingApplyViewTest(AbstractViewTestCaseNoSignals):
    """
    Test for game application view
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_apply"
        self.gamer3.block(self.gamer1)

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, gameid=self.gp2.slug)

    def test_blocked_view(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, gameid=self.gp2.slug)
            self.response_403()

    def test_gm_view(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, gameid=self.gp2.slug)
            self.response_302()

    def test_player_view(self):
        models.Player.objects.create(game=self.gp2, gamer=self.gamer2)
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, gameid=self.gp2.slug)
            self.response_302()

    def test_applicant_view(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, gameid=self.gp2.slug)

    def test_post_without_submit(self):
        with self.login(username=self.gamer4.username):
            post_data = {"message": "Thanks for your consideration!"}
            previous_apps = models.GamePostingApplication.objects.count()
            self.post(self.view_name, data=post_data, gameid=self.gp2.slug)
            self.response_302()
            assert previous_apps < models.GamePostingApplication.objects.count()
            assert (
                models.GamePostingApplication.objects.filter(gamer=self.gamer4)
                .latest("created")
                .status
                == "new"
            )

    def test_post_with_submit(self):
        with self.login(username=self.gamer4.username):
            post_data = {
                "message": "Thanks for your consideration!",
                "submit_app": "",
            }
            previous_apps = models.GamePostingApplication.objects.count()
            self.post(self.view_name, data=post_data, gameid=self.gp2.slug)
            self.response_302()
            assert previous_apps < models.GamePostingApplication.objects.count()
            assert (
                models.GamePostingApplication.objects.filter(gamer=self.gamer4)
                .latest("created")
                .status
                == "pending"
            )


class GamePostinApplyDetailViewTest(AbstractViewTestCaseNoSignals):
    """
    Test for viewing the detail of an application.
    """

    def setUp(self):
        super().setUp()
        self.application = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer4, message="Hi", status="new"
        )
        self.view_name = "games:game_apply_detail"
        self.url_kwargs = {"application": self.application.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_other_gamer(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm_before_submit(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_application_author(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_gm_after_submit(self):
        self.application.status = "pending"
        self.application.save()
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class GamePostingApplyUpdateViewTest(AbstractViewTestCaseNoSignals):
    """
    Test for application update view.
    """

    def setUp(self):
        super().setUp()
        self.application = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer4, message="Hi", status="new"
        )
        self.view_name = "games:game_apply_update"
        self.url_kwargs = {"application": self.application.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_other_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_post_without_submit(self):
        with self.login(username=self.gamer4.username):
            post_data = {"message": "I would like to play"}
            self.post(self.view_name, data=post_data, **self.url_kwargs)
            self.response_302()
            assert (
                "I would like to play"
                == models.GamePostingApplication.objects.get(
                    pk=self.application.id
                ).message
            )
            assert (
                models.GamePostingApplication.objects.get(pk=self.application.id).status
                == "new"
            )

    def test_post_with_submit(self):
        with self.login(username=self.gamer4.username):
            post_data = {"message": "I would like to play", "submit_app": ""}
            self.post(self.view_name, data=post_data, **self.url_kwargs)
            self.response_302()
            assert (
                "I would like to play"
                == models.GamePostingApplication.objects.get(
                    pk=self.application.id
                ).message
            )
            assert (
                models.GamePostingApplication.objects.get(pk=self.application.id).status
                == "pending"
            )


class GamePostingApplyWithdrawViewTest(AbstractViewTestCaseNoSignals):
    """
    Test for deleting an application.
    """

    def setUp(self):
        super().setUp()
        self.application = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer4, message="Hi", status="pending"
        )
        self.view_name = "games:game_apply_delete"
        self.url_kwargs = {"application": self.application.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_other_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_delete(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.GamePostingApplication.objects.get(pk=self.application.pk)


class GamePostingAppliedListTest(AbstractViewTestCaseNoSignals):
    """
    Test user's personal application list.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:my-game-applications"
        self.application1 = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer4, message="Hi", status="pending"
        )
        self.application2 = models.GamePostingApplication.objects.create(
            game=self.gp3, gamer=self.gamer4, message="Pick me!", status="new"
        )
        self.application3 = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer4, message="Try again", status="deny"
        )
        self.application4 = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer3, message="You up?", status="approve"
        )

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_good_load(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name)
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name)


class GamePostingApplicationApproveTest(AbstractViewTestCaseNoSignals):
    """
    Test approval reject view for player applications.
    """

    def setUp(self):
        super().setUp()
        self.application = models.GamePostingApplication.objects.create(
            game=self.gp2, gamer=self.gamer3, message="You up?", status="pending"
        )
        self.view_name = "games:game_application_approve_reject"
        self.url_kwargs = {"application": self.application.slug}

    def test_post_required(self):
        self.get(self.view_name, **self.url_kwargs)
        self.response_405()

    def test_login_required(self):
        self.post(self.view_name, data={"status": "approve"}, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_unauthorized_user(self):
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data={"status": "approve"}, **self.url_kwargs)
            self.response_403()

    def test_authorized_approval(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data={"status": "approve"}, **self.url_kwargs)
            self.response_302()
            assert (
                models.GamePostingApplication.objects.get(id=self.application.id).status
                == "approve"
            )
            assert models.Player.objects.get(game=self.gp2, gamer=self.gamer3)

    def test_authorized_reject(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data={"status": "deny"}, **self.url_kwargs)
            self.response_302()
            assert (
                models.GamePostingApplication.objects.get(id=self.application.id).status
                == "deny"
            )


class GamePostingUpdateTest(AbstractViewTestCaseNoSignals):
    def setUp(self):
        super().setUp()
        self.view_name = "games:game_edit"
        self.url_kwargs = {"gameid": self.gp2.slug}
        self.valid_post_data = {
            "title": "A Valid Campaign",
            "game_type": "campaign",
            "status": "open",
            "privacy_level": "private",
            "min_players": 1,
            "max_players": 3,
            "game_description": "Some of us enjoy cake, too.",
            "session_length": 2.5,
            "game_frequency": "weekly",
            "communities": [self.comm1.pk],
        }
        self.invalid_post_data = {
            "title": "A Valid Campaign",
            "game_type": "campaign",
            "status": "open",
            "privacy_level": "private",
            "min_players": 1,
            "max_players": 3,
            "game_description": "I ate a whole pie once.",
            "session_length": 2.5,
            "game_frequency": "weekly",
            "communities": [self.comm2.pk],
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_other_user(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_invalid_community(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.invalid_post_data, **self.url_kwargs)
            self.response_200()
            assert len(self.get_context("form").errors) > 0

    def test_valid_submission(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.valid_post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.GamePosting.objects.get(pk=self.gp2.pk).title
                == "A Valid Campaign"
            )


class GamePostingDeleteTest(AbstractViewTestCaseNoSignals):
    """
    Test for deleting a game posting.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_delete"
        self.url_kwargs = {"gameid": self.gp2.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_other_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_delete(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.GamePosting.objects.get(pk=self.gp2.pk)


class AbstractGameSessionTest(AbstractViewTestCaseSignals):
    """
    Makes the process of setting up game session tests less repetitive.
    """

    fixtures = ["rule"]

    def setUp(self):
        super().setUp()
        self.gp2.refresh_from_db()
        self.gp2.start_time = timezone.now() - timedelta(days=6)
        self.gp2.save()
        assert self.gp2.event
        self.session1 = self.gp2.create_next_session()
        self.session1.status = "complete"
        self.session1.save()
        self.gp2.refresh_from_db()
        self.session2 = self.gp2.create_next_session()
        models.Player.objects.create(gamer=self.gamer4, game=self.gp2)

    def test_session_amount(self):
        assert models.GameSession.objects.filter(game=self.gp2).count() == 2


class GameSessionListTest(AbstractGameSessionTest):
    """
    Posting for game session list.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_list"
        self.url_kwargs = {"gameid": self.gp2.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_player(self):
        models.Player.objects.create(gamer=self.gamer4, game=self.gp2)
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            assert (
                len(self.get_context("session_list"))
                == models.GameSession.objects.filter(game=self.gp2).count()
            )


class GameSessionAdHocCreateTest(AbstractGameSessionTest):
    """
    Test view for creating a game session in an ad hoc manner.
    """

    def setUp(self):
        super().setUp()
        models.Player.objects.create(gamer=self.gamer4, game=self.gp2)
        self.view_name = "games:session_adhoc_create"
        self.url_kwargs = {"gameid": self.gp2.slug}
        self.post_data = {
            "scheduled_time": (timezone.now() + timedelta(days=1)).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "players_expected": [
                f.pk for f in models.Player.objects.filter(game=self.gp2)
            ],
            "players_missing": [],
            "gm_notes": "",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm_but_closed(self):
        self.session2.status = "complete"
        self.session2.save()
        self.gp2.status = "closed"
        self.gp2.save()
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_302()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_valid_update(self):
        session_count = models.GameSession.objects.filter(game=self.gp2).count()
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.GameSession.objects.count() - session_count == 1


class GameSessionCreateTest(AbstractGameSessionTest):
    """
    Game Session create view.
    """

    def setUp(self):
        super().setUp()
        models.Player.objects.create(gamer=self.gamer4, game=self.gp2)
        self.view_name = "games:session_create"
        self.url_kwargs = {"gameid": self.gp2.slug}
        self.post_data = {"game": self.gp2.pk}

    def test_login_required(self):
        self.post(self.view_name, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def get_not_allowed(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_405()

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_gm_but_open_session(self):
        with mute_signals(post_save):
            with self.login(username=self.gamer1.username):
                session_count = models.GameSession.objects.filter(game=self.gp2).count()
                self.post(self.view_name, data=self.post_data, **self.url_kwargs)
                self.response_302()
                assert (
                    session_count
                    == models.GameSession.objects.filter(game=self.gp2).count()
                )

    def test_gm_game_over(self):
        with mute_signals(post_save):
            self.session2.status = "complete"
            self.session2.save()
            self.gp2.status = "closed"
            self.gp2.save()
            with self.login(username=self.gamer1.username):
                session_count = models.GameSession.objects.filter(game=self.gp2).count()
                self.post(self.view_name, data=self.post_data, **self.url_kwargs)
                assert (
                    session_count
                    == models.GameSession.objects.filter(game=self.gp2).count()
                )

    def test_gm_sessions_closed(self):
        with mute_signals(post_save):
            self.session2.status = "complete"
            self.session2.save()
            with self.login(username=self.gamer1.username):
                session_count = models.GameSession.objects.filter(game=self.gp2).count()
                self.post(self.view_name, data=self.post_data, **self.url_kwargs)
                self.response_302()
                assert (
                    models.GameSession.objects.filter(game=self.gp2).count()
                    - session_count
                    == 1
                )
                newest_session = models.GameSession.objects.filter(
                    game=self.gp2
                ).latest("scheduled_time")
                assert self.last_response["location"] == reverse(
                    "games:session_edit", kwargs={"session": newest_session.slug}
                )


class GameSessionDetailTest(AbstractGameSessionTest):
    """
    Test for session detail view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_detail"
        self.url_kwargs = {"session": self.session1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_player(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_gm_access(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class GameSessionUpdateTest(AbstractGameSessionTest):
    """
    Test for session update view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_edit"
        self.url_kwargs = {"session": self.session2.slug}
        self.session2.refresh_from_db()
        self.post_data = {
            "players_expected": [
                f.pk for f in models.Player.objects.filter(game=self.gp2)
            ],
            "players_missing": [],
            "gm_notes": "This will be wild and **wacky**!",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_player_only(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm_load(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_update(self):
        with self.login(username=self.gamer1.username):
            print(self.post_data)
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors(self.last_response)
            self.response_302()
            assert (
                models.GameSession.objects.get(pk=self.session2.pk).gm_notes
                == "This will be wild and **wacky**!"
            )


class GameSessionCompleteTest(AbstractGameSessionTest):
    """
    Test for completion and undo completion.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_complete_toggle"
        self.url_kwargs = {"session": self.session2.slug}
        self.session2.refresh_from_db()
        self.post_complete_data = {"status": "complete"}
        self.post_pending_data = {"status": "pending"}
        self.post_cancel_data = {"status": "cancel"}

    def test_post_required(self):
        self.get(self.view_name, **self.url_kwargs)
        self.response_405()

    def test_login_required(self):
        self.post(self.view_name, data=self.post_complete_data, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_unauthorized_user(self):
        with self.login(username=self.gamer3.username):
            self.post(self.view_name, data=self.post_complete_data, **self.url_kwargs)
            self.response_403()

    def test_authoriized_user_bad_status(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_cancel_data, **self.url_kwargs)
            assert (
                models.GameSession.objects.get(pk=self.session2.pk).status == "pending"
            )

    def test_authorized_user_valid_posts(self):
        with self.login(username=self.gamer1.username):
            with mute_signals(post_save):
                self.post(
                    self.view_name, data=self.post_complete_data, **self.url_kwargs
                )
                self.response_302()
                assert (
                    models.GameSession.objects.get(pk=self.session2.pk).status
                    == "complete"
                )
                self.post(
                    self.view_name, data=self.post_pending_data, **self.url_kwargs
                )
                self.response_302()
                assert (
                    models.GameSession.objects.get(pk=self.session2.pk).status
                    == "pending"
                )


class GameSessionMoveTest(AbstractGameSessionTest):
    """
    Test for rescheduling a game session.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_move"
        self.url_kwargs = {"session": self.session2.slug}
        self.post_data = {
            "scheduled_time": (
                self.session2.scheduled_time + timedelta(days=1)
            ).strftime("%Y-%m-%d %H:%M")
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            original_time = self.session2.scheduled_time
            with mute_signals(post_save):
                self.post(self.view_name, data=self.post_data, **self.url_kwargs)
                if self.last_response.status_code == 200:
                    self.print_form_errors()
                self.response_302()
                updated_session = models.GameSession.objects.get(pk=self.session2.pk)
                assert original_time < updated_session.scheduled_time
                assert (
                    updated_session.scheduled_time == updated_session.occurrence.start
                )


class GameSessionCancelTest(AbstractGameSessionTest):
    """
    Test canceling a game session.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_cancel"
        self.url_kwargs = {"session": self.session2.slug}
        self.post_data = {"status": "cancel"}

    def test_post_required(self):
        self.get(self.view_name, **self.url_kwargs)
        self.response_405()

    def test_login_required(self):
        self.post(self.view_name, data=self.post_data, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]
        assert models.GameSession.objects.get(pk=self.session2.pk).status != "cancel"

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            with mute_signals(post_save):
                self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            updated_session = models.GameSession.objects.get(pk=self.session2.pk)
            assert updated_session.status == "cancel"
            assert updated_session.occurrence.cancelled


class GameSessionUncancelTest(AbstractGameSessionTest):
    """
    Test uncancelling a game session.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:session_uncancel"
        self.url_kwargs = {"session": self.session2.slug}
        self.post_data = {"status": "pending"}
        with mute_signals(post_save):
            self.session2.cancel()

    def test_post_required(self):
        self.get(self.view_name, **self.url_kwargs)
        self.response_405()

    def test_login_required(self):
        self.post(self.view_name, data=self.post_data, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]
        assert models.GameSession.objects.get(pk=self.session2.pk).status == "cancel"

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            with mute_signals(post_save):
                self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            updated_session = models.GameSession.objects.get(pk=self.session2.pk)
            assert updated_session.status == "pending"
            assert not updated_session.occurrence.cancelled


class AdventureLogCreateTest(AbstractGameSessionTest):
    """
    Test for creation of an adventure log.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:log_create"
        self.url_kwargs = {"session": self.session2.slug}
        self.post_data = {
            "title": "Mystery in the deep",
            "body": "Our heroes encountered a lot of **stuff**.",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_player(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_submit_creation(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.AdventureLog.objects.filter(session=self.session2)
                .latest("created")
                .initial_author
                == self.gamer4
            )


class AdventureLogUpdateTest(AbstractGameSessionTest):
    """Test for editing an adventure log."""

    def setUp(self):
        super().setUp()
        self.log = models.AdventureLog.objects.create(
            session=self.session2,
            initial_author=self.gamer4,
            title="Mystery in the deep",
            body="Our heroes encountered a lot of **stuff**",
        )
        self.view_name = "games:log_edit"
        self.url_kwargs = {"log": self.log.slug}
        self.post_data = {
            "title": "Mystery in the deep",
            "body": "Our heroes fight an octopus",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_update_submit(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            assert (
                models.AdventureLog.objects.get(pk=self.log.pk).body
                == "Our heroes fight an octopus"
            )
            assert (
                models.AdventureLog.objects.get(pk=self.log.pk).last_edited_by
                == self.gamer1
            )


class AdventureLogDeleteTest(AbstractGameSessionTest):
    """
    Test deletion of an adventure log.
    """

    def setUp(self):
        super().setUp()
        self.log = models.AdventureLog.objects.create(
            session=self.session2,
            initial_author=self.gamer4,
            title="Mystery in the deep",
            body="Our heroes encountered a lot of **stuff**",
        )
        self.view_name = "games:log_delete"
        self.url_kwargs = {"log": self.log.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_player_only(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_deletion(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            with pytest.raises(ObjectDoesNotExist):
                models.AdventureLog.objects.get(pk=self.log.pk)


class CalendarDetailTest(AbstractViewTestCaseNoSignals):

    fixtures = ["rule"]

    def setUp(self):
        super().setUp()
        self.gp2.start_time = timezone.now() + timedelta(days=2)
        self.gp2.game_frequency = "weekly"
        self.gp2.session_length = 2.5
        with mute_signals(post_save):
            self.gp2.save()
        self.view_name = "games:calendar_detail"
        self.url_kwargs = {"gamer": self.gamer1.username}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class CalendarJSONTest(AbstractAPITestCase):
    fixtures = ["rule"]

    def setUp(self):
        super().setUp()
        self.gp2.start_time = timezone.now() + timedelta(days=2)
        self.gp2.game_frequency = "weekly"
        self.gp2.session_length = 2.5
        with mute_signals(post_save):
            self.gp2.save()
        self.view_name = "games:api_occurrences"
        self.query_values = {
            "calendar_slug": self.gamer1.username,
            "start": mkfirstOfmonth(timezone.now()).strftime("%Y-%m-%d"),
            "end": mkLastOfMonth(timezone.now()).strftime("%Y-%m-%d"),
            "timezone": timezone.now().strftime("%Z"),
        }
        self.query_string = urllib.parse.urlencode(self.query_values)
        self.request_url = "{}?{}".format(
            self.reverse(self.view_name), self.query_string
        )

    def test_login_required(self):
        self.last_response = self.client.get(self.request_url)
        self.response_302()

    def test_invalid_user(self):
        print(self.request_url)
        with self.login(username=self.gamer3.username):
            self.last_response = self.client.get(self.request_url)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer1.username):
            self.last_response = self.client.get(self.request_url)
            self.response_200()


class PlayerLeaveTest(AbstractViewTestCaseSignals):
    """
    Test for player leave view
    """

    def setUp(self):
        super().setUp()
        with mute_signals(post_save):
            self.player1 = models.Player.objects.create(
                game=self.gp2, gamer=self.gamer4
            )
        self.view_name = "games:player_leave"
        self.url_kwargs = {"gameid": self.gp2.slug, "player": self.player1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_leave_submit(self):
        with self.login(username=self.gamer4.username):
            with mute_signals(pre_delete):
                self.post(self.view_name, data={}, **self.url_kwargs)
                self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.Player.objects.get(pk=self.player1.pk)


class PlayerKickTest(AbstractViewTestCaseSignals):
    """
    Test for kicking a player.
    """

    def setUp(self):
        super().setUp()
        self.player1 = models.Player.objects.create(game=self.gp2, gamer=self.gamer4)
        self.view_name = "games:player_kick"
        self.url_kwargs = {"gameid": self.gp2.slug, "player": self.player1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_kick_submit(self):
        with self.login(username=self.gamer1.username):
            with mute_signals(pre_delete):
                self.post(self.view_name, data={}, **self.url_kwargs)
                self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.Player.objects.get(pk=self.player1.pk)


class CharacterCreateTest(AbstractViewTestCaseSignals):
    """
    Test for player character models.
    """

    def setUp(self):
        super().setUp()
        self.player1 = models.Player.objects.create(game=self.gp2, gamer=self.gamer4)
        self.view_name = "games:character_create"
        self.url_kwargs = {"player": self.player1.slug}
        self.post_data = {"name": "Magic Brian", "description": "Elven wizard"}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_user(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_creation(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            assert models.Character.objects.get(player=self.player1, name="Magic Brian")


class AbstractCharacterManipTests(AbstractViewTestCaseSignals):
    """
    Automates some of the setup for the following tests.
    """

    def setUp(self):
        super().setUp()
        self.player1 = models.Player.objects.create(game=self.gp2, gamer=self.gamer4)
        self.character1 = models.Character.objects.create(
            player=self.player1,
            name="Magic Brian",
            game=self.gp2,
            description="Elven wizard",
        )


class CharacterDetailTest(AbstractCharacterManipTests):
    """
    Test for viewing character details.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_detail"
        self.url_kwargs = {"character": self.character1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_users(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class CharacterUpdateTest(AbstractCharacterManipTests):
    """
    Test for updating a character.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_edit"
        self.url_kwargs = {"character": self.character1.slug}
        self.post_data = {"name": "Magic Brian", "description": "Half-drow wizard"}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_users(self):
        for gamer in [self.gamer4, self.gamer1]:
            with self.login(username=gamer.username):
                self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_submit_edit(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.Character.objects.get(pk=self.character1.pk).description
                == "Half-drow wizard"
            )


class CharacterDeleteTest(AbstractCharacterManipTests):
    """
    Test for deleting a character.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_delete"
        self.url_kwargs = {"character": self.character1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_valid_users(self):
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_deletion(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data={}, **self.url_kwargs)


class CharacterApproveTest(AbstractCharacterManipTests):
    """
    Test for character approval.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_approve"
        self.url_kwargs = {"character": self.character1.slug}
        self.post_data = {"status": "approved"}

    def test_post_required(self):
        self.get(self.view_name, **self.url_kwargs)
        self.response_405()

    def test_login_required(self):
        self.post(self.view_name, data=self.post_data, **self.url_kwargs)
        self.response_302()
        assert "accounts/login" in self.last_response["location"]

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.Character.objects.get(pk=self.character1.pk).status == "approved"
            )


class CharacterRejectTest(CharacterApproveTest):
    """
    Test for character rejection.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_reject"
        self.post_data["status"] = "rejected"

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.Character.objects.get(pk=self.character1.pk).status == "rejected"
            )


class CharacterInactiveTest(CharacterApproveTest):
    """
    Test for making a character inactive.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_inactivate"
        self.post_data["status"] = "inactive"

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_403()

    def test_player(self):
        with self.login(username=self.gamer4.username):
            print(self.post_data)
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.Character.objects.get(pk=self.character1.pk).status == "inactive"
            )


class CharacterReactivateTest(CharacterInactiveTest):
    """
    Test for character reactivation.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_reactivate"
        self.post_data["status"] == "pending"

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert (
                models.Character.objects.get(pk=self.character1.pk).status == "pending"
            )


class AbstractCharacterListTest(AbstractCharacterManipTests):
    """
    Abstract Test for list view
    """

    def setUp(self):
        super().setUp()
        self.player2 = models.Player.objects.create(game=self.gp2, gamer=self.gamer2)
        self.character2 = models.Character.objects.create(
            player=self.player2,
            game=self.gp2,
            name="Taakko the wise",
            description="Halfling shapeshifter",
        )
        self.expected_value = 1


class CharacterGameListTest(AbstractCharacterListTest):
    """
    Test for list for a given game.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_game_list"
        self.url_kwargs = {"gameid": self.gp2.slug}
        self.expected_value = 2

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_members(self):
        for gamer in [self.gamer2, self.gamer4, self.gamer1]:
            with self.login(username=gamer.username):
                self.assertGoodView(self.view_name, **self.url_kwargs)
                assert self.expected_value == len(self.get_context("character_list"))


class CharacterPlayerListTest(CharacterGameListTest):
    """
    Test for viewing list of characters associated with a single player in a game.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:character_player_list"
        self.url_kwargs = {"player": self.player1.slug}
        self.expected_value = 1


class CharacterGamerList(AbstractCharacterListTest):
    """
    Test for character list for a given gamer.
    """

    def setUp(self):
        super().setUp()
        self.player3 = models.Player.objects.create(game=self.gp1, gamer=self.gamer2)
        self.character3 = models.Character.objects.create(
            player=self.player3,
            game=self.gp1,
            name="Rosebud",
            description="A magical sled",
        )
        self.expected_value = 2
        self.view_name = "games:character_gamer_list"

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_valid_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name)
            assert self.expected_value == len(self.get_context("character_list"))


class GameInviteListTest(AbstractViewTestCaseNoSignals):
    """
    Test the invite list view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_invite_list"
        self.url_kwargs = {"slug": self.gp2.slug}
        for x in range(3):
            Invite.objects.create(
                creator=self.gamer1.user,
                label="test {}".format(x),
                content_object=self.gp2,
            )

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_player(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_gm(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class GameExportTest(AbstractGameSessionTest):
    """
    Test export view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = 'games:game_export'
        self.url_kwargs = {'gameid': self.gp2.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_unauthorized_user(self):
        for gamer in [self.gamer2, self.gamer4]:
            with self.login(username=gamer.username):
                self.get(self.view_name, **self.url_kwargs)
                self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class ProfileExportTest(AbstractGameSessionTest):
    """
    Export an entire profile.
    """
    def setUp(self):
        super().setUp()
        self.view_name = 'gamer_profiles:profile_export'
        self.url_kwargs = {'gamer': self.gamer1.username}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_unauthrorized_user(self):
        with self.login(username=self.gamer4.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
