import logging
from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.utils import timezone
from factory.django import mute_signals
from notifications.models import Notification

from .. import models, tasks
from ..tests.fixtures import GamesTData

pytestmark = pytest.mark.django_db(transaction=True)

logger = logging.getLogger("games")


def test_eventedit_update_child_events(game_testdata):
    with mute_signals(post_save, post_delete):
        start_time = timezone.now() + timedelta(days=2)
        end_time = start_time + timedelta(hours=2)
        event = models.GameEvent.objects.create(
            calendar=game_testdata.calendar1,
            creator=game_testdata.gamer1.user,
            start=start_time,
            end=end_time,
            title="Example Event",
            description="Something Something",
        )
        # Create some child events.
        event.generate_missing_child_events(
            [game_testdata.calendar2, game_testdata.calendar3]
        )
        child_events = event.get_child_events()
        for cev in child_events:
            assert cev.title == event.title
            assert cev.description == event.description
        event.description = "Something New!"
        event.title = "Eat me."
        event.save()
        child_events = event.get_child_events()
        for cev in child_events:
            assert cev.title != event.title
            assert cev.description != event.description
        tasks.update_child_events_for_master(event)
        child_events = event.get_child_events()
        for cev in child_events:
            assert cev.title == event.title
            assert cev.description == event.description


def task_for_generating_player_events(game_testdata):
    with mute_signals(post_save):
        start_time = timezone.now() + timedelta(days=2)
        game_testdata.gp1.start_time = start_time
        game_testdata.gp1.game_frequency = "weekly"
        game_testdata.gp1.save()
        assert game_testdata.gp1.event
        models.Player.objects.create(gamer=game_testdata.gamer2, game=game_testdata.gp1)
        models.Player.objects.create(gamer=game_testdata.gamer3, game=game_testdata.gp1)
        assert not game_testdata.gp1.event.get_child_events()
        tasks.create_game_player_events(game_testdata.gp1)
        assert game_testdata.gp1.event.get_child_events().count() == 2


def test_child_occurrence_sync(game_testdata):
    with mute_signals(post_save):
        start_time = timezone.now() + timedelta(days=2)
        game_testdata.gp1.start_time = start_time
        game_testdata.gp1.game_frequency = "weekly"
        game_testdata.gp1.save()
        assert game_testdata.gp1.event
        models.Player.objects.create(gamer=game_testdata.gamer2, game=game_testdata.gp1)
        models.Player.objects.create(gamer=game_testdata.gamer3, game=game_testdata.gp1)
        tasks.create_game_player_events(game_testdata.gp1)
        occurences = game_testdata.gp1.event.occurrences_after(
            after=timezone.now() + timedelta(weeks=2)
        )
        occ_to_edit = next(occurences)
        occ_to_edit.move(
            new_start=occ_to_edit.start + timedelta(days=1),
            new_end=occ_to_edit.end + timedelta(days=1),
        )
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 0
        )
        tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 3
        )
        occ_to_edit.move(
            new_start=occ_to_edit.start + timedelta(hours=1),
            new_end=occ_to_edit.end + timedelta(hours=1),
        )
        tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
        child_occ_links = models.ChildOccurenceLink.objects.filter(
            master_event_occurence=occ_to_edit
        ).all()
        assert child_occ_links.count() == 3
        for link in child_occ_links:
            assert link.master_event_occurence.start == link.child_event_occurence.start
            assert link.master_event_occurence.end == link.child_event_occurence.end


def test_calendar_sync_for_arriving_player(game_testdata):
    with mute_signals(post_save):
        start_time = timezone.now() + timedelta(days=2)
        game_testdata.gp1.start_time = start_time
        game_testdata.gp1.game_frequency = "weekly"
        game_testdata.gp1.save()
        assert game_testdata.gp1.event
        models.Player.objects.create(gamer=game_testdata.gamer2, game=game_testdata.gp1)
        models.Player.objects.create(gamer=game_testdata.gamer3, game=game_testdata.gp1)
        tasks.create_game_player_events(game_testdata.gp1)
        occurences = game_testdata.gp1.event.occurrences_after(
            after=timezone.now() + timedelta(weeks=2)
        )
        occ_to_edit = next(occurences)
        occ_to_edit.move(
            new_start=occ_to_edit.start + timedelta(days=1),
            new_end=occ_to_edit.end + timedelta(days=1),
        )
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 0
        )
        tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
        player3 = models.Player.objects.create(
            gamer=game_testdata.gamer4, game=game_testdata.gp1
        )
        assert game_testdata.gp1.event.get_child_events().count() == 3
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 3
        )
        tasks.sync_calendar_for_arriving_player(player3)
        assert game_testdata.gp1.event.get_child_events().count() == 4
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 4
        )


def test_calendar_clear_for_departing_player(game_testdata):
    with mute_signals(post_save, post_delete, pre_delete):
        start_time = timezone.now() + timedelta(days=2)
        game_testdata.gp1.start_time = start_time
        game_testdata.gp1.game_frequency = "weekly"
        logger.debug("TESTS: Calling save on gp1 to trigger event creation...")
        game_testdata.gp1.save()
        assert game_testdata.gp1.event
        logger.debug(
            "TESTS: Creating additional players, which should NOT generate events for them yet."
        )
        models.Player.objects.create(gamer=game_testdata.gamer2, game=game_testdata.gp1)
        models.Player.objects.create(gamer=game_testdata.gamer3, game=game_testdata.gp1)
        logger.debug("TESTS: Now explicitly generating events for players...")
        tasks.create_game_player_events(game_testdata.gp1)
        occurences = game_testdata.gp1.event.occurrences_after(
            after=timezone.now() + timedelta(weeks=2)
        )
        occ_to_edit = next(occurences)
        logger.debug(
            "TESTS: Moving occurrence. Since post_save is muted this should not create player occurrences yet."
        )
        occ_to_edit.move(
            new_start=occ_to_edit.start + timedelta(days=1),
            new_end=occ_to_edit.end + timedelta(days=1),
        )
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 0
        )
        logger.debug("TESTS: Now explicitly generating player occurrences and links.")
        tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
        logger.debug(
            "TESTS: Now additing an additional player... which should not create additional events yet."
        )
        player3 = models.Player.objects.create(
            gamer=game_testdata.gamer4, game=game_testdata.gp1
        )
        assert game_testdata.gp1.event.get_child_events().count() == 3
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 3
        )
        logger.debug("TESTS: Now explicitly creating events for player.")
        tasks.sync_calendar_for_arriving_player(player3)
        assert game_testdata.gp1.event.get_child_events().count() == 4
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 4
        )
        # since we aren't useing the delete signal here, we can't just delete
        # the player.
        logger.debug(
            "TESTS: Now explicitly removing player events and deleting player."
        )
        tasks.clear_calendar_for_departing_player(player3)
        player3.delete()
        assert (
            models.ChildOccurenceLink.objects.filter(
                master_event_occurence=occ_to_edit
            ).count()
            == 3
        )
        assert game_testdata.gp1.event.get_child_events().count() == 3


class GamesNotifyTData(GamesTData):
    def __init__(self):
        super().__init__()
        self.game = models.GamePosting.objects.create(
            game_type="campaign",
            title="My Awesome Adventure",
            min_players=2,
            max_players=5,
            session_length=2.5,
            game_description="We will roll dice!",
            gm=self.gamer1,
        )
        with mute_signals(m2m_changed):
            self.game.communities.add(self.comm1, self.comm2)
        self.comm1.add_member(self.gamer2)
        self.member_rec = self.comm1.members.get(gamer=self.gamer2)
        self.member_rec.game_notifications = True
        self.member_rec.save()
        self.member_rec2 = self.comm2.members.get(gamer=self.gamer2)
        self.member_rec2.game_notifications = True
        self.member_rec2.save()


@pytest.fixture
def game_notify_testdata():
    ContentType.objects.clear_cache()
    yield GamesNotifyTData()
    ContentType.objects.clear_cache()


def test_notify_one_community(game_notify_testdata):
    all_notifications = Notification.objects.count()
    g3_notifications = Notification.objects.filter(
        recipient=game_notify_testdata.gamer2.user
    ).count()
    tasks.notify_subscribers_of_new_game(
        [game_notify_testdata.comm1], game_notify_testdata.game
    )
    assert Notification.objects.count() - all_notifications == 1
    assert (
        Notification.objects.filter(recipient=game_notify_testdata.gamer2.user).count()
        - g3_notifications
        == 1
    )


def test_notify_multiple_communities(game_notify_testdata):
    all_notifications = Notification.objects.count()
    g2_notifications = Notification.objects.filter(
        recipient=game_notify_testdata.gamer2.user
    ).count()
    tasks.notify_subscribers_of_new_game(
        [game_notify_testdata.comm1, game_notify_testdata.comm2],
        game_notify_testdata.game,
    )
    assert Notification.objects.count() - all_notifications == 1
    assert (
        Notification.objects.filter(recipient=game_notify_testdata.gamer2.user).count()
        - g2_notifications
        == 1
    )


def test_notify_multiple_comms_but_only_one_optin(game_notify_testdata):
    game_notify_testdata
    game_notify_testdata.member_rec2.game_notifications = False
    game_notify_testdata.member_rec2.save()
    all_notifications = Notification.objects.count()
    g2_notifications = Notification.objects.filter(
        recipient=game_notify_testdata.gamer2.user
    ).count()
    tasks.notify_subscribers_of_new_game(
        [game_notify_testdata.comm1, game_notify_testdata.comm2],
        game_notify_testdata.game,
    )
    assert Notification.objects.count() - all_notifications == 1
    assert (
        Notification.objects.filter(recipient=game_notify_testdata.gamer2.user).count()
        - g2_notifications
        == 1
    )


def test_notify_multiple_comms_but_no_optin(game_notify_testdata):
    game_notify_testdata.member_rec.game_notifications = False
    game_notify_testdata.member_rec.save()
    game_notify_testdata.member_rec2.game_notifications = False
    game_notify_testdata.member_rec2.save()
    all_notifications = Notification.objects.count()
    g2_notifications = Notification.objects.filter(
        recipient=game_notify_testdata.gamer2.user
    ).count()
    tasks.notify_subscribers_of_new_game(
        [game_notify_testdata.comm1, game_notify_testdata.comm2],
        game_notify_testdata.game,
    )
    assert Notification.objects.count() - all_notifications == 0
    assert (
        Notification.objects.filter(recipient=game_notify_testdata.gamer2.user).count()
        - g2_notifications
        == 0
    )


def test_notify_long_name_one(game_notify_testdata):
    new_name = "".join("a" for x in range(255))
    game_notify_testdata.comm1.name = new_name
    game_notify_testdata.comm1.save()
    all_notifications = Notification.objects.count()
    g2_notifications = Notification.objects.filter(
        recipient=game_notify_testdata.gamer2.user
    ).count()
    tasks.notify_subscribers_of_new_game(
        [game_notify_testdata.comm1], game_notify_testdata.game
    )
    assert Notification.objects.count() - all_notifications == 1
    assert (
        Notification.objects.filter(recipient=game_notify_testdata.gamer2.user).count()
        - g2_notifications
        == 1
    )
    assert "..." in Notification.objects.latest("timestamp").verb


def test_long_name_multiple(game_notify_testdata):
    new_name = "".join("a" for x in range(255))
    game_notify_testdata.comm1.name = new_name
    game_notify_testdata.comm1.save()
    all_notifications = Notification.objects.count()
    g2_notifications = Notification.objects.filter(
        recipient=game_notify_testdata.gamer2.user
    ).count()
    tasks.notify_subscribers_of_new_game(
        [game_notify_testdata.comm1, game_notify_testdata.comm2],
        game_notify_testdata.game,
    )
    assert Notification.objects.count() - all_notifications == 1
    assert (
        Notification.objects.filter(recipient=game_notify_testdata.gamer2.user).count()
        - g2_notifications
        == 1
    )
    assert "..." in Notification.objects.latest("timestamp").verb
