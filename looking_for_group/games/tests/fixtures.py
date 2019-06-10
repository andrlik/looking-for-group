from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed
from django.utils import timezone
from factory.django import mute_signals
from schedule.models import Rule

from ...gamer_profiles.tests import factories
from .. import models


class GamesTData(object):
    def __init__(self):
        ContentType.objects.clear_cache()
        self.rule1, created = Rule.objects.get_or_create(
            name="weekly", defaults={"description": "Weekly", "frequency": "WEEKLY"}
        )
        self.rule2, created = Rule.objects.get_or_create(
            name="monthly", defaults={"description": "Monthly", "frequency": "MONTHLY"}
        )
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        self.gamer4 = factories.GamerProfileFactory()
        self.comm1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.comm2 = factories.GamerCommunityFactory(owner=self.gamer2)
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
        with mute_signals(m2m_changed):
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
        self.gp2.refresh_from_db()
        self.gp2.start_time = timezone.now() - timedelta(days=6)
        self.gp2.save()
        assert self.gp2.event
        self.session1 = self.gp2.create_next_session()
        self.session1.status = "complete"
        self.session1.save()
        self.gp2.refresh_from_db()
        self.session2 = self.gp2.create_next_session()
        self.player1 = models.Player.objects.create(gamer=self.gamer4, game=self.gp2)
        self.character1 = models.Character.objects.create(
            player=self.player1,
            name="Magic Brian",
            game=self.gp2,
            description="Elven wizard",
        )
        self.log1 = models.AdventureLog.objects.create(
            session=self.session2,
            initial_author=self.gamer4,
            title="Mystery in the deep",
            body="Our heroes encountered a lot of **stuff**",
        )


@pytest.fixture
def game_testdata(transactional_db):
    yield GamesTData()
    ContentType.objects.clear_cache()


@pytest.fixture
def game_gamer_to_use(game_testdata):
    return game_testdata.gamer1


@pytest.fixture
def game_game_to_use(game_testdata):
    return game_testdata.gp2


@pytest.fixture
def game_character_to_use(game_testdata):
    return game_testdata.character1


@pytest.fixture
def game_session_to_use(game_testdata):
    return game_testdata.session1


@pytest.fixture
def game_log_to_use(game_testdata):
    return game_testdata.log1