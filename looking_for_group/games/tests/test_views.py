from django.test import TransactionTestCase
from factory.django import mute_signals
from test_plus import TestCase

from .. import models
from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory


class AbstractViewTestCase(object):
    def setUp(self):
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
        )


class AbstractViewTestCaseNoSignals(AbstractViewTestCase, TestCase):
    pass


class AbstractViewTestCaseSignals(AbstractViewTestCase, TransactionTestCase):
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


class GamePostingCreateTest(AbstractViewTestCaseNoSignals):
    """
    Test creation of a game posting.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "games:game_create"
        self.valid_post_data = {
            "title": "A Valid Campaign",
            "game_type": "campaign",
            "privacy_level": "private",
            "min_players": 1,
            "max_players": 3,
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
                "submit_app": None,
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
    pass


class GamePostingApplyWithdrawViewTest(AbstractViewTestCaseNoSignals):
    pass


class GamePostingAppliedListTest(AbstractViewTestCaseNoSignals):
    pass


class GamePostingUpdateTest(AbstractViewTestCaseNoSignals):
    pass


class GamePostingDeleteTest(AbstractViewTestCaseNoSignals):
    pass


class GameSessionListTest(AbstractViewTestCaseNoSignals):
    pass


class GameSessionCreateTest(AbstractViewTestCaseNoSignals):
    pass


class GameSessionDetailTest(AbstractViewTestCaseNoSignals):
    pass


class GameSessionUpdateTest(AbstractViewTestCaseNoSignals):
    pass


class GameSessionMoveTest(AbstractViewTestCaseNoSignals):
    pass


class GameSessionDeleteTest(AbstractViewTestCaseNoSignals):
    pass


class AdventureLogListTest(AbstractViewTestCaseNoSignals):
    pass


class AdventureLogDetailTest(AbstractViewTestCaseNoSignals):
    pass


class AdventureLogCreateTest(AbstractViewTestCaseNoSignals):
    pass


class AdventureLogUpdateTest(AbstractViewTestCaseNoSignals):
    pass


class AdventureLogDeleteTest(AbstractViewTestCaseNoSignals):
    pass


class CalendarDetailTest(AbstractViewTestCaseNoSignals):
    pass


class CalendarJSONTest(AbstractViewTestCaseNoSignals):
    pass
