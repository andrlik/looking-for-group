from datetime import timedelta
import pytest
from test_plus import TestCase
from factory.django import mute_signals
from django.test import TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import (post_save)
from schedule.models import Rule, Calendar
from ...gamer_profiles.tests import factories
from .. import models


class AbstractSyncTestCase(TestCase):
    def setUp(self):
        self.rule1, created = Rule.objects.get_or_create(name='weekly', defaults={'description': 'Weekly', 'frequency': 'WEEKLY'})
        self.rule2, created = Rule.objects.get_or_create(name='monthly', defaults={'description': 'Monthly', 'frequency': 'MONTHLY'})
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        with mute_signals(post_save):
            self.game = models.GamePosting.objects.create(game_type='campaign', title='My Awesome Adventure', min_players=2, max_players=5, session_length=2.5, game_description="We will roll dice!", gm=self.gamer1)
            self.calendar1, created = Calendar.objects.get_or_create(slug=self.gamer1.username, defaults={'name': "{}'s calendar".format(self.gamer1.username)})
            self.calendar2, created = Calendar.objects.get_or_create(slug=self.gamer2.username, defaults={'name': "{}'s calendar".format(self.gamer2.username)})
            self.calendar3, created = Calendar.objects.get_or_create(slug=self.gamer3.username, defaults={'name': "{}'s calendar".format(self.gamer3.username)})


class AbstractAsyncTestCase(TransactionTestCase):
    def setUp(self):
        self.rule1, created = Rule.objects.get_or_create(name='weekly', defaults={'description': 'Weekly', 'frequency': 'WEEKLY'})
        self.rule2, created = Rule.objects.get_or_create(name='monthly', defaults={'description': 'Monthly', 'frequency': 'MONTHLY'})
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        with mute_signals(post_save):
            self.game = models.GamePosting.objects.create(game_type='campaign', title='My Awesome Adventure', min_players=2, max_players=5, session_length=2.5, game_description="We will roll dice!", gm=self.gamer1)
            self.calendar1, created = Calendar.objects.get_or_create(slug=self.gamer1.username, defaults={'name': "{}'s calendar".format(self.gamer1.username)})
            self.calendar2, created = Calendar.objects.get_or_create(slug=self.gamer2.username, defaults={'name': "{}'s calendar".format(self.gamer2.username)})
            self.calendar3, created = Calendar.objects.get_or_create(slug=self.gamer3.username, defaults={'name': "{}'s calendar".format(self.gamer3.username)})


class TestEventCreationSignal(AbstractSyncTestCase):

    def test_dont_create_event(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'na'
            self.game.save()
            assert not self.game.event

    def test_create_single_occurrence_event(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'na'
            self.game.start_time = timezone.now() + timedelta(days=2)
            self.game.save()
            assert self.game.event
            assert not self.game.event.rule
            assert self.game.event.start == self.game.start_time
            assert self.game.event.end == self.game.start_time + timedelta(minutes=(60 * self.game.session_length))

    def test_create_ongoing_event(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'weekly'
            self.game.start_time = timezone.now() + timedelta(days=2)
            self.game.save()
            assert self.game.event
            assert self.game.event.rule

    def test_delete_event(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'weekly'
            self.game.start_time = timezone.now() + timedelta(days=2)
            self.game.save()
            assert self.game.event
            event = self.game.event
            self.game.start_time = None
            self.game.save()
            assert not self.game.event
            with pytest.raises(ObjectDoesNotExist):
                models.GameEvent.objects.get(pk=event.pk)

    def test_update_existing_event(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'weekly'
            self.game.start_time = timezone.now() + timedelta(days=2)
            self.game.save()
            assert self.game.event
            event_rule = self.game.event.rule
            assert event_rule.name == self.game.game_frequency
            self.game.start_time = self.game.start_time + timedelta(days=3)
            self.game.game_frequency = 'na'
            self.game.save()
            assert not self.game.event.rule
            assert self.game.event.start == self.game.start_time
            assert self.game.event.end == self.game.start_time + timedelta(minutes=(60 * self.game.session_length))
            self.game.title = 'Ooga ooga'
            self.game.save()
            assert self.game.event.title == self.game.title


class MarkdownSignalTest(AbstractSyncTestCase):

    def test_game_posting_markdown(self):
        with mute_signals(post_save):
            self.game.game_description = "I am very **strong**!"
            self.game.save()
            assert self.game.game_description_rendered == "<p>I am very <strong>strong</strong>!</p>"

    def test_adventure_log_markdown(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'weekly'
            self.game.start_time = timezone.now() - timedelta(days=2)
            self.game.save()
            assert self.game.event
            session = self.game.create_session_from_occurrence(self.game.get_next_scheduled_session_occurrence())
            assert session
            ad_log = models.AdventureLog.objects.create(session=session, initial_author=self.gamer2, title='My Log Entry', body="I am very **strong**!")
            assert ad_log.body_rendered == "<p>I am very <strong>strong</strong>!</p>"

    def test_gm_notes_markdown(self):
        with mute_signals(post_save):
            self.game.game_frequency = 'weekly'
            self.game.start_time = timezone.now() - timedelta(days=2)
            self.game.save()
            session = self.game.create_session_from_occurrence(self.game.get_next_scheduled_session_occurrence())
            assert session
            session.gm_notes = "I am very **strong**!"
            session.save()
            assert session.gm_notes_rendered == "<p>I am very <strong>strong</strong>!</p>"
