from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed
from django.utils import timezone
from factory.django import mute_signals
from test_plus import TestCase

from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory
from .. import forms
from ..models import GamePosting, Player

pytestmark = pytest.mark.django_db(transaction=True)


class TFormData(object):
    """
    Store some reusable values.
    """

    def __init__(self):
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.comm1 = GamerCommunityFactory(owner=self.gamer1)
        self.comm2 = GamerCommunityFactory(owner=self.gamer2)
        self.gamer4 = GamerProfileFactory()


class TSessionFormData(TFormData):
    def __init__(self):
        super().__init__()
        self.game = GamePosting.objects.create(
            gm=self.gamer1,
            game_type="campaign",
            min_players=1,
            title="A spooky adventure",
            max_players=5,
            game_frequency="weekly",
            session_length=3.0,
        )
        with mute_signals(m2m_changed):
            self.game.communities.add(self.comm1)
        self.player1 = Player.objects.create(gamer=self.gamer2, game=self.game)
        self.player2 = Player.objects.create(gamer=self.gamer3, game=self.game)
        self.player3 = Player.objects.create(gamer=self.gamer4, game=self.game)
        self.game2 = GamePosting.objects.create(
            gm=self.gamer2,
            game_type="campaign",
            min_players=1,
            title="A silly adventure",
            max_players=5,
            game_frequency="weekly",
            session_length=3.0,
        )
        self.player4 = Player.objects.create(gamer=self.gamer1, game=self.game2)


@pytest.fixture
def gameform_testdata():
    ContentType.objects.clear_cache()
    yield TFormData()
    ContentType.objects.clear_cache()


@pytest.fixture
def sessionform_testdata():
    ContentType.objects.clear_cache()
    yield TSessionFormData()
    ContentType.objects.clear_cache()


def test_gameform_community_queryset(gameform_testdata):
    form = forms.GamePostingForm(gamer=gameform_testdata.gamer1)
    assert form.fields["communities"].queryset.count() == 1
    assert form.fields["communities"].queryset.all()[0] == gameform_testdata.comm1
    gameform_testdata.comm2.add_member(gameform_testdata.gamer1)
    gameform_testdata.gamer1.refresh_from_db()
    form2 = forms.GamePostingForm(gamer=gameform_testdata.gamer1)
    assert form2.fields["communities"].queryset.count() == 2
    form3 = forms.GamePostingForm(gamer=gameform_testdata.gamer4)
    assert "communities" not in form3.fields.keys()


def test_gameform_privacyvscommunities(gameform_testdata):
    """
    Ensures that a private form where a community is selected is not valid.
    """
    data = {
        "gm": gameform_testdata.gamer1.id,
        "title": "A new fun game",
        "game_type": "campaign",
        "game_mode": "online",
        "min_players": 1,
        "max_players": 4,
        "game_frequency": "weekly",
        "session_length": 2.5,
        "privacy_level": "private",
        "communities": [gameform_testdata.comm1.pk],
    }
    form = forms.GamePostingForm(data, gamer=gameform_testdata.gamer1)
    assert not form.is_valid()
    assert len(form["privacy_level"].errors) == 1
    assert len(form["communities"].errors) == 1


def test_gamerform_invalid_call():
    with pytest.raises(KeyError):
        forms.GamePostingForm()


def test_sessionform_player_queryset(sessionform_testdata):
    form = forms.GameSessionForm(game=sessionform_testdata.game)
    assert form.fields["players_expected"].queryset.count() == 3
    assert form.fields["players_missing"].queryset.count() == 3
    form2 = forms.GameSessionForm(game=sessionform_testdata.game2)
    assert form2.fields["players_expected"].queryset.count() == 1
    assert form2.fields["players_missing"].queryset.count() == 1


def test_sessonform_validate_initiial_data():
    with pytest.raises(KeyError):
        forms.GameSessionForm()


def test_sessionform_validate_players(sessionform_testdata):
    form = forms.GameSessionForm(
        {
            "scheduled_time": timezone.now() + timedelta(days=1),
            "players_expected": [
                sessionform_testdata.player1,
                sessionform_testdata.player2,
                sessionform_testdata.player4,
            ],
            "players_missing": [],
        },
        game=sessionform_testdata.game,
    )
    assert not form.is_valid()


def test_sessionform_missing_not_exceed_expected(sessionform_testdata):
    form = forms.GameSessionForm(
        {
            "scheduled_time": timezone.now() + timedelta(days=1),
            "players_expected": [
                sessionform_testdata.player1,
                sessionform_testdata.player2,
            ],
            "players_missing": [sessionform_testdata.player3],
        },
        game=sessionform_testdata.game,
    )
    assert not form.is_valid()
    form2 = forms.GameSessionForm(
        {
            "scheduled_time": timezone.now() + timedelta(days=1),
            "players_expected": [],
            "players_missing": [sessionform_testdata.player3],
        },
        game=sessionform_testdata.game,
    )
    assert not form2.is_valid()


def test_sessionform_validate_good_data(sessionform_testdata):
    form = forms.GameSessionForm(
        {
            "scheduled_time": timezone.now() + timedelta(days=1),
            "players_expected": [
                sessionform_testdata.player1,
                sessionform_testdata.player2,
                sessionform_testdata.player3,
            ],
            "players_missing": [sessionform_testdata.player3],
        },
        game=sessionform_testdata.game,
    )
    assert form.is_valid()


def test_filter_form_render(gameform_testdata):
    """
    Test that the filter form disables distance correctly.
    """
    filter_form = forms.GameFilterForm()
    assert filter_form.fields["distance"].disabled
    filter_form2 = forms.GameFilterForm(profile_has_city=True)
    assert not filter_form2.fields["distance"].disabled
