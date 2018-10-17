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
        self.gp1 = models.GamePosting.objects.create(game_type='campaign', title='A spoopy campaign', gm=self.gamer4, privacy_level='public', min_players=1, max_players=5, game_frequency='weekly', session_length=2.5)
        self.gp4 = models.GamePosting.objects.create(game_type='campaign', title='A spoopy campaign', gm=self.gamer4, privacy_level='private', min_players=1, max_players=5, game_frequency='weekly', session_length=2.5)
        self.gp2 = models.GamePosting.objects.create(game_type='campaign', title='A community campaign', gm=self.gamer1, privacy_level='community', min_players=1, max_players=5, game_frequency='weekly', session_length=2.5)
        self.gp2.communities.add(self.comm1)
        self.gp3 = models.GamePosting.objects.create(game_type='campaign', title='A private game', gm=self.gamer3, privacy_level='private', min_players=1, max_players=5, game_frequency='weekly', session_length=2.5)
        self.gp5 = models.GamePosting.objects.create(game_type='campaign', status='cancel', title='A spoopy campaign', gm=self.gamer4, privacy_level='public', min_players=1, max_players=5, game_frequency='weekly', session_length=2.5)


class AbstractViewTestCaseNoSignals(AbstractViewTestCase, TestCase):
    pass


class AbstractViewTestCaseSignals(AbstractViewTestCase, TransactionTestCase):
    pass


class GamePostingListTest(AbstractViewTestCaseNoSignals):
    '''
    Test the game posting list view.
    '''

    def setUp(self):
        super().setUp()
        self.view_name = 'games:game_list'

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_visability(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name)
            games = self.get_context('game_list')
            assert games.count() == 2
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name)
            games = self.get_context('game_list')
            assert games.count() == 1
        with self.login(username=self.gamer3.username):
            self.assertGoodView(self.view_name)
            games = self.get_context('game_list')
            assert games.count() == 3
        with self.login(username=self.gamer4.username):
            self.assertGoodView(self.view_name)
            games = self.get_context('game_list')
            assert games.count() == 3


class GamePostingCreateTest(AbstractViewTestCaseNoSignals):
    pass


class GamePostingDetailTest(AbstractViewTestCaseNoSignals):
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
