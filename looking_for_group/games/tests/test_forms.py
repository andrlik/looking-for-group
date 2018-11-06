from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase as TestCase
from django.utils import timezone

from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory
from ..forms import GamePostingForm, GameSessionForm, GameSessionRescheduleForm
from ..models import GamePosting, Player


class AbstractFormTest(TestCase):
    """
    Make our setup less tedious.
    """

    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.comm1 = GamerCommunityFactory(owner=self.gamer1)
        self.comm2 = GamerCommunityFactory(owner=self.gamer2)
        self.gamer4 = GamerProfileFactory()


class GamePostingFormTest(AbstractFormTest):
    def test_commmunity_queryset(self):
        form = GamePostingForm(gamer=self.gamer1)
        assert form.fields["communities"].queryset.count() == 1
        assert form.fields["communities"].queryset.all()[0] == self.comm1
        self.comm2.add_member(self.gamer1)
        self.gamer1.refresh_from_db()
        form2 = GamePostingForm(gamer=self.gamer1)
        assert form2.fields["communities"].queryset.count() == 2
        assert self.comm2 in form2.fields["communities"].queryset.all()
        form3 = GamePostingForm(gamer=self.gamer4)
        assert "communities" not in form3.fields.keys()

    def test_invalid_call(self):
        with pytest.raises(KeyError):
            GamePostingForm()


class GameSessionFormTest(AbstractFormTest):
    '''
    Tests for game session call.
    '''

    def setUp(self):
        super().setUp()
        self.game = GamePosting.objects.create(gm=self.gamer1, game_type='campaign', min_players=1, title='A spooky adventure', max_players=5, game_frequency='weekly', session_length=3.0)
        self.game.communities.add(self.comm1)
        self.player1 = Player.objects.create(gamer=self.gamer2, game=self.game)
        self.player2 = Player.objects.create(gamer=self.gamer3, game=self.game)
        self.player3 = Player.objects.create(gamer=self.gamer4, game=self.game)
        self.game2 = GamePosting.objects.create(gm=self.gamer2, game_type='campaign', min_players=1, title='A silly adventure', max_players=5, game_frequency='weekly', session_length=3.0)
        self.player4 = Player.objects.create(gamer=self.gamer1, game=self.game2)

    def test_player_queryset(self):
        form = GameSessionForm(game=self.game)
        assert form.fields['players_expected'].queryset.count() == 3
        assert form.fields['players_missing'].queryset.count() == 3
        form2 = GameSessionForm(game=self.game2)
        assert form2.fields['players_expected'].queryset.count() == 1
        assert form2.fields['players_missing'].queryset.count() == 1

    def test_invalid_init_data(self):
        with pytest.raises(KeyError):
            GameSessionForm()

    def test_validate_only_valid_players(self):
        form = GameSessionForm({'scheduled_time': timezone.now() + timedelta(days=1), 'players_expected': [self.player1, self.player2, self.player4], 'players_missing': []}, game=self.game)
        assert not form.is_valid()

    def test_validate_missing_not_exceed_expected(self):
        form = GameSessionForm({'scheduled_time': timezone.now() + timedelta(days=1), 'players_expected': [self.player1, self.player2], 'players_missing': [self.player3]}, game=self.game)
        assert not form.is_valid()
        form2 = GameSessionForm({'scheduled_time': timezone.now() + timedelta(days=1), 'players_expected': [], 'players_missing': [self.player3]}, game=self.game)
        assert not form2.is_valid()

    def test_validate_good_data(self):
        form = GameSessionForm({'scheduled_time': timezone.now() + timedelta(days=1), 'players_expected': [self.player1, self.player2, self.player3], 'players_missing':[self.player3]}, game=self.game)
        assert form.is_valid()
