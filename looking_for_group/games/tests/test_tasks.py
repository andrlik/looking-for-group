from datetime import timedelta

from django.db.models.signals import post_delete, post_save, pre_delete
from django.utils import timezone
from factory.django import mute_signals
from notifications.models import Notification
from schedule.models import Calendar, Rule
from test_plus import TestCase

from ...gamer_profiles.tests import factories
from .. import models, tasks


class AbstractTaskTestCase(TestCase):
    """
    Tests the tasks that would normally run in signals
    however we will mute signals here in order to atomically
    test the methods themselves.
    """

    def setUp(self):
        self.rule1, created = Rule.objects.get_or_create(
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


class TestEventEdits(AbstractTaskTestCase):
    """
    Tests the tasks that would normally run in signals
    however we will mute signals here in order to atomically
    test the methods themselves.
    """

    def setUp(self):
        super().setUp()

    def test_update_child_events(self):
        with mute_signals(post_save, post_delete):
            start_time = timezone.now() + timedelta(days=2)
            end_time = start_time + timedelta(hours=2)
            event = models.GameEvent.objects.create(
                calendar=self.calendar1,
                creator=self.gamer1.user,
                start=start_time,
                end=end_time,
                title="Example Event",
                description="Something Something",
            )
            # Create some child events.
            event.generate_missing_child_events(
                [self.calendar2, self.calendar3]
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

    def test_task_for_generating_player_event(self):
        with mute_signals(post_save):
            start_time = timezone.now() + timedelta(days=2)
            self.game.start_time = start_time
            self.game.game_frequency = "weekly"
            self.game.save()
            assert self.game.event
            models.Player.objects.create(gamer=self.gamer2, game=self.game)
            models.Player.objects.create(gamer=self.gamer3, game=self.game)
            assert not self.game.event.get_child_events()
            tasks.create_game_player_events(self.game)
            assert self.game.event.get_child_events().count() == 2

    def test_child_occurence_sync(self):
        with mute_signals(post_save):
            start_time = timezone.now() + timedelta(days=2)
            self.game.start_time = start_time
            self.game.game_frequency = "weekly"
            self.game.save()
            assert self.game.event
            models.Player.objects.create(gamer=self.gamer2, game=self.game)
            models.Player.objects.create(gamer=self.gamer3, game=self.game)
            tasks.create_game_player_events(self.game)
            occurences = self.game.event.occurrences_after(
                after=timezone.now() + timedelta(weeks=2)
            )
            occ_to_edit = next(occurences)
            occ_to_edit.move(
                new_start=occ_to_edit.start + timedelta(days=1),
                new_end=occ_to_edit.end + timedelta(days=1),
            )
            assert models.ChildOccurenceLink.objects.count() == 0
            tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
            assert models.ChildOccurenceLink.objects.count() == 2
            occ_to_edit.move(
                new_start=occ_to_edit.start + timedelta(hours=1),
                new_end=occ_to_edit.end + timedelta(hours=1),
            )
            tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
            child_occ_links = models.ChildOccurenceLink.objects.all()
            assert child_occ_links.count() == 2
            for link in child_occ_links:
                assert (
                    link.master_event_occurence.start
                    == link.child_event_occurence.start
                )
                assert link.master_event_occurence.end == link.child_event_occurence.end

    def test_calendar_sync_for_arriving_player(self):
        with mute_signals(post_save):
            start_time = timezone.now() + timedelta(days=2)
            self.game.start_time = start_time
            self.game.game_frequency = "weekly"
            self.game.save()
            assert self.game.event
            models.Player.objects.create(gamer=self.gamer2, game=self.game)
            models.Player.objects.create(gamer=self.gamer3, game=self.game)
            tasks.create_game_player_events(self.game)
            occurences = self.game.event.occurrences_after(
                after=timezone.now() + timedelta(weeks=2)
            )
            occ_to_edit = next(occurences)
            occ_to_edit.move(
                new_start=occ_to_edit.start + timedelta(days=1),
                new_end=occ_to_edit.end + timedelta(days=1),
            )
            assert models.ChildOccurenceLink.objects.count() == 0
            tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
            self.gamer4 = factories.GamerProfileFactory()
            player3 = models.Player.objects.create(gamer=self.gamer4, game=self.game)
            assert self.game.event.get_child_events().count() == 2
            assert models.ChildOccurenceLink.objects.count() == 2
            tasks.sync_calendar_for_arriving_player(player3)
            assert self.game.event.get_child_events().count() == 3
            assert models.ChildOccurenceLink.objects.count() == 3

    def test_calendar_clear_for_departing_player(self):
        with mute_signals(post_save, post_delete, pre_delete):
            start_time = timezone.now() + timedelta(days=2)
            self.game.start_time = start_time
            self.game.game_frequency = "weekly"
            self.game.save()
            assert self.game.event
            models.Player.objects.create(gamer=self.gamer2, game=self.game)
            models.Player.objects.create(gamer=self.gamer3, game=self.game)
            tasks.create_game_player_events(self.game)
            occurences = self.game.event.occurrences_after(
                after=timezone.now() + timedelta(weeks=2)
            )
            occ_to_edit = next(occurences)
            occ_to_edit.move(
                new_start=occ_to_edit.start + timedelta(days=1),
                new_end=occ_to_edit.end + timedelta(days=1),
            )
            assert models.ChildOccurenceLink.objects.count() == 0
            tasks.create_or_update_linked_occurences_on_edit(occ_to_edit)
            self.gamer4 = factories.GamerProfileFactory()
            player3 = models.Player.objects.create(gamer=self.gamer4, game=self.game)
            assert self.game.event.get_child_events().count() == 2
            assert models.ChildOccurenceLink.objects.count() == 2
            tasks.sync_calendar_for_arriving_player(player3)
            assert self.game.event.get_child_events().count() == 3
            assert models.ChildOccurenceLink.objects.count() == 3
            # since we aren't useing the delete signal here, we can't just delete
            # the player.
            tasks.clear_calendar_for_departing_player(player3)
            player3.delete()
            assert models.ChildOccurenceLink.objects.count() == 2
            assert self.game.event.get_child_events().count() == 2


class TestNotificationTask(AbstractTaskTestCase):
    """
    Test for community notification options.
    """

    def setUp(self):
        super().setUp()
        self.community1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.community1.add_member(self.gamer2)
        self.game.communities.add(self.community1)
        member_rec = self.community1.members.get(gamer=self.gamer2)
        member_rec.game_notifications = True
        member_rec.save()

    def test_notify(self):
        all_notifications = Notification.objects.count()
        g2_notifications = Notification.objects.filter(recipient=self.gamer2.user).count()
        tasks.notify_subscribers_of_new_game(self.community1, self.game)
        assert Notification.objects.count() - all_notifications == 1
        assert Notification.objects.filter(recipient=self.gamer2.user).count() - g2_notifications == 1
