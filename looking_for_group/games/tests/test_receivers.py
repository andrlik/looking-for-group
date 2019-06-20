from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.utils import timezone
from factory.django import mute_signals
# from notifications.models import Notification
from schedule.models import Calendar, Rule

from ...gamer_profiles.tests import factories
from .. import models

pytestmark = pytest.mark.django_db(transaction=True)


class ReceiverTData(object):
    def __init__(self):
        e1, created = Rule.objects.get_or_create(
            name="weekly", defaults={"description": "Weekly", "frequency": "WEEKLY"}
        )
        self.rule2, created = Rule.objects.get_or_create(
            name="monthly", defaults={"description": "Monthly", "frequency": "MONTHLY"}
        )
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        with mute_signals(post_save):
            self.game = models.GamePosting.objects.create(
                game_type="campaign",
                title="My Awesome Adventure",
                min_players=2,
                max_players=5,
                session_length=2.5,
                game_description="We will roll dice!",
                gm=self.gamer1,
            )
            self.calendar1, created = Calendar.objects.get_or_create(
                slug=self.gamer1.username,
                defaults={"name": "{}'s calendar".format(self.gamer1.username)},
            )
            self.calendar2, created = Calendar.objects.get_or_create(
                slug=self.gamer2.username,
                defaults={"name": "{}'s calendar".format(self.gamer2.username)},
            )
            self.calendar3, created = Calendar.objects.get_or_create(
                slug=self.gamer3.username,
                defaults={"name": "{}'s calendar".format(self.gamer3.username)},
            )


@pytest.fixture
def game_receiver_testdata():
    ContentType.objects.clear_cache()
    yield ReceiverTData()
    ContentType.objects.clear_cache()


def test_dont_create_event(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "na"
        game_receiver_testdata.game.save()
        assert not game_receiver_testdata.game.event


def test_create_single_occurrence(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "na"
        game_receiver_testdata.game.start_time = timezone.now() + timedelta(days=2)
        game_receiver_testdata.game.save()
        assert game_receiver_testdata.game.event
        assert not game_receiver_testdata.game.event.rule
        assert (
            game_receiver_testdata.game.event.start
            == game_receiver_testdata.game.start_time
        )
        assert (
            game_receiver_testdata.game.event.end
            == game_receiver_testdata.game.start_time
            + timedelta(minutes=(60 * game_receiver_testdata.game.session_length))
        )


def test_create_ongoing_event(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "weekly"
        game_receiver_testdata.game.start_time = timezone.now() + timedelta(days=2)
        game_receiver_testdata.game.save()
        assert game_receiver_testdata.game.event
        assert game_receiver_testdata.game.event.rule


def test_delete_event(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "weekly"
        game_receiver_testdata.game.start_time = timezone.now() + timedelta(days=2)
        game_receiver_testdata.game.save()
        assert game_receiver_testdata.game.event
        event = game_receiver_testdata.game.event
        game_receiver_testdata.game.start_time = None
        game_receiver_testdata.game.save()
        assert not game_receiver_testdata.game.event
        with pytest.raises(ObjectDoesNotExist):
            models.GameEvent.objects.get(pk=event.pk)


def test_update_existing_event(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "weekly"
        game_receiver_testdata.game.start_time = timezone.now() + timedelta(days=2)
        game_receiver_testdata.game.save()
        assert game_receiver_testdata.game.event
        event_rule = game_receiver_testdata.game.event.rule
        assert event_rule.name == game_receiver_testdata.game.game_frequency
        game_receiver_testdata.game.start_time = (
            game_receiver_testdata.game.start_time + timedelta(days=3)
        )
        game_receiver_testdata.game.game_frequency = "na"
        game_receiver_testdata.game.save()
        assert not game_receiver_testdata.game.event.rule
        assert (
            game_receiver_testdata.game.event.start
            == game_receiver_testdata.game.start_time
        )
        assert (
            game_receiver_testdata.game.event.end
            == game_receiver_testdata.game.start_time
            + timedelta(minutes=(60 * game_receiver_testdata.game.session_length))
        )
        game_receiver_testdata.game.title = "Ooga ooga"
        game_receiver_testdata.game.save()
        assert (
            game_receiver_testdata.game.event.title == game_receiver_testdata.game.title
        )


def test_gameposting_markdown(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_description = "I am very **strong**!"
        game_receiver_testdata.game.save()
        assert (
            game_receiver_testdata.game.game_description_rendered
            == "<p>I am very <strong>strong</strong>!</p>"
        )


def test_adventurelog_markdown(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "weekly"
        game_receiver_testdata.game.start_time = timezone.now() - timedelta(days=2)
        game_receiver_testdata.game.save()
        assert game_receiver_testdata.game.event
        session = game_receiver_testdata.game.create_session_from_occurrence(
            game_receiver_testdata.game.get_next_scheduled_session_occurrence()
        )
        assert session
        ad_log = models.AdventureLog.objects.create(
            session=session,
            initial_author=game_receiver_testdata.gamer2,
            title="My Log Entry",
            body="I am very **strong**!",
        )
        assert ad_log.body_rendered == "<p>I am very <strong>strong</strong>!</p>"


def test_gmnotes_markdown(game_receiver_testdata):
    with mute_signals(post_save):
        game_receiver_testdata.game.game_frequency = "weekly"
        game_receiver_testdata.game.start_time = timezone.now() - timedelta(days=2)
        game_receiver_testdata.game.save()
        session = game_receiver_testdata.game.create_session_from_occurrence(
            game_receiver_testdata.game.get_next_scheduled_session_occurrence()
        )
        assert session
        session.gm_notes = "I am very **strong**!"
        session.save()
        assert session.gm_notes_rendered == "<p>I am very <strong>strong</strong>!</p>"
