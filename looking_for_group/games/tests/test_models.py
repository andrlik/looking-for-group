from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.test import TransactionTestCase
from django.utils import timezone
from factory.django import mute_signals
from schedule.models import Calendar, Rule

from .. import models
from ...gamer_profiles.tests import factories
from ..utils import check_table_exists


class UtilTest(TransactionTestCase):
    """
    Basic test for tables.
    """

    def test_table_review(self):
        assert check_table_exists("games_gameposting")
        assert not check_table_exists("jkdfjlsdjdsfj")


class AbstractGamesModelTest(TransactionTestCase):
    """
    Provides the repetitive setup needs.
    """

    def setUp(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        self.community1 = factories.GamerCommunityFactory(
            owner=factories.GamerProfileFactory()
        )
        self.community2 = factories.GamerCommunityFactory(owner=self.gamer2)
        self.rule1, created = Rule.objects.get_or_create(
            name="weekly", defaults={"description": "Weekly", "frequency": "WEEKLY"}
        )
        self.rule2, created = Rule.objects.get_or_create(
            name="monthly", defaults={"description": "Monthly", "frequency": "MONTHLY"}
        )
        self.start_time = timezone.now() + timedelta(days=2)
        self.end_time = self.start_time + timedelta(hours=3)
        self.game_posting = models.GamePosting.objects.create(
            game_type="campaign",
            title="My Awesome Adventure",
            min_players=2,
            max_players=5,
            session_length=2.5,
            game_description="We will roll dice!",
            gm=self.gamer1,
        )
        self.game_posting.communities.add(self.community1)
        self.player1 = models.Player.objects.create(
            gamer=self.gamer2, game=self.game_posting
        )
        self.player2 = models.Player.objects.create(
            gamer=self.gamer3, game=self.game_posting
        )


class GameEventProxyMethods(AbstractGamesModelTest):
    """
    Test that the methods for our proxy model work correctly.
    """

    def setUp(self):
        super().setUp()
        self.rule1, created = Rule.objects.get_or_create(
            name="weekly", defaults={"description": "Weekly", "frequency": "WEEKLY"}
        )
        self.rule2, created = Rule.objects.get_or_create(
            name="monthly", defaults={"description": "Monthly", "frequency": "MONTHLY"}
        )
        self.master_calendar = Calendar.objects.create(
            name="{}'s Calendar".format(self.gamer1.username), slug=self.gamer1.username
        )
        self.player_calendar1 = Calendar.objects.create(
            name="{}'s Calendar".format(self.gamer2.username), slug=self.gamer2.username
        )
        self.player_calendar2 = Calendar.objects.create(
            name="{}'s Calendar".format(self.gamer3.username), slug=self.gamer3.username
        )
        self.start_time = timezone.now() + timedelta(days=2)
        self.end_time = self.start_time + timedelta(hours=3)
        self.master_event = models.GameEvent.objects.create(
            start=self.start_time,
            end=self.end_time,
            calendar=self.master_calendar,
            creator=self.gamer1.user,
            rule=self.rule1,
        )

    def test_create_child_events(self):
        with mute_signals(post_save):
            assert self.master_event.get_child_events().count() == 0
            events_added = self.master_event.generate_missing_child_events(
                [self.player_calendar1, self.player_calendar2]
            )
            assert events_added == 2
            assert self.master_event.get_child_events().count() == 2
            # Now ensure we don't duplicate
            events_added = self.master_event.generate_missing_child_events(
                [self.player_calendar1, self.player_calendar2]
            )
            assert events_added == 0
            assert self.master_event.get_child_events().count() == 2

    def test_event_type_evaluation(self):
        with mute_signals(post_save):
            self.master_event.generate_missing_child_events(
                [self.player_calendar1, self.player_calendar2]
            )
            assert self.master_event.is_master_event()
            assert not self.master_event.is_player_event()
            for event in self.master_event.child_events:
                assert not event.is_master_event()
                assert event.is_player_event()

    def test_remove_child_events(self):
        with mute_signals(post_save):
            self.master_event.generate_missing_child_events(
                [self.player_calendar1, self.player_calendar2]
            )
            assert self.master_event.get_child_events().count() == 2
            self.master_event.remove_child_events()
            assert self.master_event.get_child_events().count() == 0

    def test_cascade_deletes(self):
        with mute_signals(post_save):
            self.master_event.generate_missing_child_events(
                [self.player_calendar1, self.player_calendar2]
            )
            ids_to_check = [f.id for f in self.master_event.child_events]
            self.master_event.delete()
            for idu in ids_to_check:
                with pytest.raises(ObjectDoesNotExist):
                    models.GameEvent.objects.get(id=idu)

    def test_update_child_events(self):
        with mute_signals(post_save):
            self.master_event.generate_missing_child_events(
                [self.player_calendar1, self.player_calendar2]
            )
            self.master_event.rule = self.rule2
            self.master_event.save()
            assert self.master_event.update_child_events() == 2


class GamePostingModelMethods(AbstractGamesModelTest):
    """
    Test methods associated with the game posting model.
    """

    def setUp(self):
        super().setUp()

    def test_event_initially_blank(self):
        assert not self.game_posting.event

    def test_event_created_when_sufficient_data_added(self):
        self.game_posting.start_time = self.start_time
        self.game_posting.game_frequency = "weekly"
        self.game_posting.save()
        self.game_posting.refresh_from_db()
        assert self.game_posting.event


class GameSessionModelMethods(AbstractGamesModelTest):
    """
    Test methods associated with game session models.
    """

    # Currently no specific methods required.
    pass
