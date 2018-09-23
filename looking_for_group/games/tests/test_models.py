import pytest
from factory.django import mute_signals
from datetime import timedelta
from test_plus import TestCase
from schedule.models import Calendar, Rule
from django.utils import timezone
from django.db.models.signals import post_save
from django.core.exceptions import ObjectDoesNotExist
from ...gamer_profiles.tests.test_views import AbstractViewTest
from .. import models
from ..utils import check_table_exists


class UtilTest(TestCase):
    '''
    Basic test for tables.
    '''

    def test_table_review(self):
        assert check_table_exists('games_gameposting')
        assert not check_table_exists('jkdfjlsdjdsfj')


class AbstractGamesModelTest(AbstractViewTest):
    '''
    Provides the repetitive setup needs.
    '''

    def setUp(self):
        pass


class GameEventProxyMethods(AbstractViewTest):
    '''
    Test that the methods for our proxy model work correctly.
    '''
    def setUp(self):
        self.rule1 = Rule.objects.get_or_create(name='weekly', defaults={'description': "Weekly", 'frequency': 'WEEKLY'})
        self.rule2 = Rule.objects.get_or_create(name='monthly', defaults={'description': "Monthly", 'frequency': 'MONTHLY'})
        self.master_calendar = Calendar.objects.create(name="{}'s Calendar".format(self.gamer1.username), slug=self.gamer1.username)
        self.player_calendar1 = Calendar.objects.create(name="{}'s Calendar".format(self.gamer2.username), slug=self.gamer2.username)
        self.player_calendar2 = Calendar.objects.create(name="{}'s Calendar".format(self.gamer3.username), slug=self.gamer3.username)
        self.start_time = timezone.now() + timedelta(days=2)
        self.end_time = self.start_time + timedelta(hours=3)
        self.master_event = models.GameEvent.objects.create(start=self.start_time, end=self.end_time, calendar=self.master_calendar, creator=self.gamer1.user, rule=self.rule1)

    def test_create_child_events(self):
        assert self.master_event.child_events.count() == 0
        events_added = self.master_event.generate_missing_child_events([self.player_calendar1, self.player_calendar2])
        assert events_added == 2
        assert self.master_event.child_events.count() == 2

    def test_event_type_evaluation(self):
        self.master_event.generate_missing_child_events([self.player_calendar1, self.player_calendar2])
        assert self.master_event.is_master_event
        assert not self.master_event.is_player_event
        for event in self.master_event.child_events:
            assert not event.is_master_event
            assert event.is_player_event

    def test_remove_child_events(self):
        self.master_event.generate_missing_child_events([self.player_calendar1, self.player_calendar2])
        assert self.master_event.child_events.count() == 2
        self.master_event.remove_child_events()
        assert self.master_event.child_events.count() == 0

    def test_cascade_deletes(self):
        self.master_event.generate_missing_child_events([self.player_calendar1, self.player_calendar2])
        ids_to_check = [f.id for f in self.master_event.child_events]
        self.master_event.delete()
        for idu in ids_to_check:
            with pytest.raises(ObjectDoesNotExist):
                models.GameEvent.objects.get(id=idu)

    def test_update_child_events(self):
        self.master_event.generate_missing_child_events([self.player_calendar1, self.player_calendar2])
        self.master_event.rule = self.rule2
        with mute_signals(post_save):
            self.master_event.save()
            assert self.update_child_events() == 2


class GamePostingModelMethods(TestCase):
    '''
    Test methods associated with the game posting model.
    '''
    pass


class GameSessionModelMethods(TestCase):
    '''
    Test methods associated with game session models.
    '''
    # Currently no specific methods required.
    pass
