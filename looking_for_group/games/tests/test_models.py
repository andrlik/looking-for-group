from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.utils import timezone
from factory.django import mute_signals
from schedule.models import Calendar

from .. import models, tasks
from ..utils import check_table_exists


def test_table_review(game_testdata):
    assert check_table_exists("games_gameposting")
    assert not check_table_exists("jkjldjdsjd")


@pytest.fixture
def game_player_group_calendars(game_testdata):
    master_calendar = Calendar.objects.get(slug=game_testdata.gamer1.username)
    player_calendar1 = Calendar.objects.get(slug=game_testdata.gamer2.username)
    player_calendar2 = Calendar.objects.get(slug=game_testdata.gamer3.username)
    start_time = timezone.now() + timedelta(days=2)
    end_time = start_time + timedelta(hours=3)
    master_event = models.GameEvent.objects.create(
        start=start_time,
        end=end_time,
        calendar=master_calendar,
        creator=game_testdata.gamer1.user,
        rule=game_testdata.rule1,
    )
    return {
        "master_calendar": master_calendar,
        "player_calendar_1": player_calendar1,
        "player_calendar_2": player_calendar2,
        "master_event": master_event,
    }


def test_create_child_events(game_testdata, game_player_group_calendars):
    assert game_player_group_calendars["master_event"].get_child_events().count() == 0
    events_added = game_player_group_calendars[
        "master_event"
    ].generate_missing_child_events(
        [
            game_player_group_calendars["player_calendar_1"],
            game_player_group_calendars["player_calendar_2"],
        ]
    )
    assert events_added == 2
    events_added = game_player_group_calendars[
        "master_event"
    ].generate_missing_child_events(
        [
            game_player_group_calendars["player_calendar_1"],
            game_player_group_calendars["player_calendar_2"],
        ]
    )
    assert events_added == 0
    assert game_player_group_calendars["master_event"].get_child_events().count() == 2


def test_event_type_evaluation(game_testdata, game_player_group_calendars):
    game_player_group_calendars["master_event"].generate_missing_child_events(
        [
            game_player_group_calendars["player_calendar_1"],
            game_player_group_calendars["player_calendar_2"],
        ]
    )
    assert game_player_group_calendars["master_event"].is_master_event()
    assert not game_player_group_calendars["master_event"].is_player_event()
    for event in game_player_group_calendars["master_event"].get_child_events():
        assert not event.is_master_event()
        assert event.is_player_event()


def test_remove_child_events(game_testdata, game_player_group_calendars):
    game_player_group_calendars["master_event"].generate_missing_child_events(
        [
            game_player_group_calendars["player_calendar_1"],
            game_player_group_calendars["player_calendar_2"],
        ]
    )
    assert game_player_group_calendars["master_event"].get_child_events().count() == 2
    game_player_group_calendars["master_event"].remove_child_events()
    assert game_player_group_calendars["master_event"].get_child_events().count() == 0


def test_event_cascade_delete(game_testdata, game_player_group_calendars):
    game_player_group_calendars["master_event"].generate_missing_child_events(
        [
            game_player_group_calendars["player_calendar_1"],
            game_player_group_calendars["player_calendar_2"],
        ]
    )
    ids_to_check = [
        e.id for e in game_player_group_calendars["master_event"].get_child_events()
    ]
    game_player_group_calendars["master_event"].delete()
    for idu in ids_to_check:
        with pytest.raises(ObjectDoesNotExist):
            models.GameEvent.objects.get(pk=idu)


def test_update_child_events(game_testdata, game_player_group_calendars):
    game_player_group_calendars["master_event"].generate_missing_child_events(
        [
            game_player_group_calendars["player_calendar_1"],
            game_player_group_calendars["player_calendar_2"],
        ]
    )
    game_player_group_calendars["master_event"].rule = game_testdata.rule2
    game_player_group_calendars["master_event"].save()
    assert game_player_group_calendars["master_event"].update_child_events() == 2


def test_game_posting_initially_without_event(game_testdata):
    assert not game_testdata.gp1.event


def test_game_posting_event_created_when_enough_data(game_testdata):
    game_testdata.gp1.start_time = timezone.now() + timedelta(days=2)
    game_testdata.gp1.save()
    game_testdata.gp1.refresh_from_db()
    assert game_testdata.gp1.event


def test_gamesession_adhoc_event_generated(game_testdata):
    adhoc_session = models.GameSession.objects.create(
        game=game_testdata.gp1,
        session_type="adhoc",
        scheduled_time=timezone.now() + timedelta(days=5),
    )
    assert adhoc_session.occurrence
    assert (
        models.GameEvent.objects.get(pk=adhoc_session.occurrence.event.id)
        .get_child_events()
        .count()
        == 0
    )


def test_gamesession_adhoc_event_add_to_calendar(game_testdata):
    with mute_signals(post_save):
        adhoc_session = models.GameSession.objects.create(
            game=game_testdata.gp2,
            session_type="adhoc",
            scheduled_time=timezone.now() + timedelta(days=3),
        )
    with mute_signals(m2m_changed):
        adhoc_session.players_expected.add(game_testdata.player1, game_testdata.player2)
    tasks.update_player_calendars_for_adhoc_session(adhoc_session)
    child_events = models.GameEvent.objects.get(
        id=adhoc_session.occurrence.event.id
    ).get_child_events()
    assert child_events.count() == 2
    for ce in child_events:
        ce.calendar.slug in [
            game_testdata.player1.gamer.username,
            game_testdata.player2.gamer.username,
        ]


def test_update_adhoc_session(game_testdata):
    adhoc_session = models.GameSession.objects.create(
        game=game_testdata.gp2,
        session_type="adhoc",
        scheduled_time=timezone.now() + timedelta(days=3),
    )
    with mute_signals(m2m_changed):
        adhoc_session.players_expected.add(game_testdata.player1, game_testdata.player2)
        adhoc_session.players_expected.remove(game_testdata.player2)
    tasks.update_player_calendars_for_adhoc_session(adhoc_session)
    child_events = models.GameEvent.objects.get(
        id=adhoc_session.occurrence.event.id
    ).get_child_events()
    assert child_events.count() == 1


def test_adhoc_player_leave(game_testdata):
    adhoc_session = models.GameSession.objects.create(
        game=game_testdata.gp2,
        session_type="adhoc",
        scheduled_time=timezone.now() + timedelta(days=3),
    )
    with mute_signals(m2m_changed):
        adhoc_session.players_expected.add(game_testdata.player1, game_testdata.player2)
        tasks.update_player_calendars_for_adhoc_session(adhoc_session)
        adhoc_session.players_expected.remove(game_testdata.player2)
        tasks.update_player_calendars_for_adhoc_session(adhoc_session)
    with mute_signals(pre_delete):
        game_testdata.player2.delete()
    assert (
        models.GameEvent.objects.get(id=adhoc_session.occurrence.event.id)
        .get_child_events()
        .count()
        == 1
    )


def test_adhoc_player_clear(game_testdata):
    adhoc_session = models.GameSession.objects.create(
        game=game_testdata.gp2,
        session_type="adhoc",
        scheduled_time=timezone.now() + timedelta(days=3),
    )
    with mute_signals(m2m_changed):
        adhoc_session.players_expected.add(game_testdata.player1, game_testdata.player2)
        adhoc_session.players_expected.clear()
        tasks.update_player_calendars_for_adhoc_session(adhoc_session)
    assert (
        models.GameEvent.objects.get(id=adhoc_session.occurrence.event.id)
        .get_child_events()
        .count()
        == 0
    )
