import logging
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.db.models.signals import m2m_changed, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_q.tasks import async_task
from markdown import markdown
from notifications.signals import notify
from schedule.models import Calendar, Occurrence, Rule

from . import models
from ..invites.models import Invite
from ..invites.signals import invite_accepted
from .signals import player_kicked, player_left
from .tasks import (
    calculate_player_attendance,
    clear_calendar_for_departing_player,
    create_game_player_events,
    notify_subscribers_of_new_game,
    remove_event_and_descendants,
    sync_calendar_for_arriving_player,
    undo_player_attendence_for_incomplete_session,
    update_child_events_for_master,
    update_player_calendars_for_adhoc_session
)

logger = logging.getLogger("games")


@receiver(pre_delete, sender=models.GameEvent)
def remove_child_events_on_delete(sender, instance, *args, **kwargs):
    logger.debug(
        "Event with id {} is being deleted. Checking to see if it is a master event...".format(
            instance.id
        )
    )
    if instance.is_master_event() and instance.get_child_events().count() > 0:
        logger.error(
            "Event is a master event with child events. You are attempting to delete it while leaving them in. This WILL cause and issue."
        )
        raise ValueError(
            _(
                "You are trying to delete a master event without removing its child events!!!"
            )
        )
    else:
        logger.debug(
            "This is empty master or a child event. Proceeding to collect occurrences to delete first."
        )
        num_deleted, details = Occurrence.objects.filter(event=instance).delete()
        logger.debug(
            "Deleted {} related occurrence records with details of {}".format(
                num_deleted, details
            )
        )


@receiver(pre_save, sender=models.GamePosting)
def set_end_date_for_game_on_complete(sender, instance, *args, **kwargs):
    if instance.status in ["closed", "cancel"] and not instance.end_date:
        instance.end_date = timezone.now()


@receiver(pre_save, sender=models.GamePosting)
def render_markdown_description(sender, instance, *args, **kwargs):
    if instance.game_description:
        instance.game_description_rendered = markdown(instance.game_description)
    else:
        instance.game_description_rendered = None


@receiver(pre_save, sender=models.GameSession)
def render_markdown_notes(sender, instance, *args, **kwargs):
    if instance.gm_notes:
        instance.gm_notes_rendered = markdown(instance.gm_notes)
    else:
        instance.gm_notes_rendered = None
    try:
        old_copy = models.GameSession.objects.get(id=instance.pk)
        if instance.status != "complete" and old_copy.status == "complete":
            undo_player_attendence_for_incomplete_session(old_copy)
    except ObjectDoesNotExist:
        pass  # This is a new session so no need to worry.


@receiver(pre_save, sender=models.AdventureLog)
def render_markdown_log_body(sender, instance, *args, **kwargs):
    if instance.body:
        instance.body_rendered = markdown(instance.body)
    else:
        instance.body_rendered = None


@receiver(post_save, sender=models.AdventureLog)
def notify_on_log_create_edit(sender, instance, created, *args, **kwargs):
    if created:
        for player in instance.session.players_expected.all():
            if instance.initial_author != player.gamer:
                notify.send(
                    instance.initial_author,
                    recipient=player.gamer.user,
                    verb="posted a new adventure log",
                    target=instance.session,
                )
        if instance.initial_author != instance.session.game.gm:
            notify.send(
                instance.initial_author,
                recipient=instance.session.game.gm.user,
                verb="posted a new adventure log",
                target=instance.session,
            )


@receiver(post_save, sender=models.GameSession)
def update_complete_session_count(sender, instance, *args, **kwargs):
    instance.game.update_completed_session_count()


@receiver(post_save, sender=models.GameSession)
def calculate_attendance(sender, instance, created, *args, **kwargs):
    if instance.status == "complete":
        async_task(calculate_player_attendance, instance)


@receiver(pre_save, sender=models.GamePosting)
def create_update_event_for_game(sender, instance, *args, **kwargs):
    """
    If the game has enough information to generate an event, check if one already exists and link to it.
    """
    if instance.start_time and instance.session_length:
        if instance.game_frequency in ("na", "Custom"):
            frequency = None
        else:
            frequency = instance.game_frequency
        logger.debug("Game posting has enough data to have a corresponding event.")
        if instance.event:
            logger.debug(
                "Event already exists. Reviewing to see if changes are required..."
            )
            needs_edit = False
            if instance.start_time != instance.event.start:
                needs_edit = True
                logger.debug("Updating start time to {}".format(instance.start_time))
                instance.event.start = instance.start_time
            if instance.event.end != instance.start_time + timedelta(
                minutes=int(60 * instance.session_length)
            ):
                instance.event.end = instance.start_time + timedelta(
                    minutes=int(60 * instance.session_length)
                )
                logger.debug("Updating end time to {}".format(instance.event.end))
                needs_edit = True
            if instance.event.end_recurring_period != instance.end_date:
                logger.debug("End date has changed...")
                instance.event.end_recurring_period = instance.end_date
                needs_edit = True
            if frequency:
                try:
                    rrule = Rule.objects.get(name=instance.game_frequency)
                    if instance.event.rule != rrule:
                        needs_edit = True
                        instance.event.rule = rrule
                        logger.debug("Updating rule to {}".format(rrule.name))
                except ObjectDoesNotExist:
                    # Something is very wrong here.
                    raise ValueError("Invalid frequency type!")
            else:
                instance.event.rule = None
            if (
                instance.event.title != instance.title
                or instance.event.description != instance.game_description
            ):
                needs_edit = True
                instance.event.title = instance.title
                instance.event.description = instance.game_description
            if needs_edit:
                logger.debug("Changes were made, saving.")
                instance.event.save()
            else:
                logger.debug("No changes required.")
        else:
            logger.debug(
                "Event does not exist yet. Creating and adding to GM's calendar."
            )
            calendar, created = Calendar.objects.get_or_create(
                slug=instance.gm.username,
                defaults={"name": "{}'s Calendar".format(instance.gm.username)},
            )
            if created:
                logger.debug(
                    "Created new calendar for user {} with slug {}".format(
                        instance.gm.username, calendar.slug
                    )
                )
            rule = None
            if frequency:
                rule = Rule.objects.get(name=frequency)
            instance.event = models.GameEvent.objects.create(
                start=instance.start_time,
                end=(
                    instance.start_time
                    + timedelta(minutes=int(60 * instance.session_length))
                ),
                end_recurring_period=instance.end_date,
                title=instance.title,
                description=instance.game_description,
                creator=instance.gm.user,
                rule=rule,
                calendar=calendar,
            )
    else:
        logger.debug("Insufficient data for an event.")
        if instance.event:
            logger.debug("There is an event associated with this. Deleting it.")
            logger.debug("Event to delete has id of {}".format(instance.event.id))
            event_to_kill = instance.event
            logger.debug("Setting game instance event to null...")
            instance.event = None
            logger.debug(
                "Sending async task to delete event with id {}".format(event_to_kill.id)
            )
            async_task(remove_event_and_descendants, event_to_kill)


@receiver(post_save, sender=models.GamePosting)
def update_games_created_count(sender, instance, created, *args, **kwargs):
    if created:
        instance.gm.games_created = F("games_created") + 1
        instance.gm.save()


@receiver(post_save, sender=models.GameEvent)
def update_child_events_when_master_event_updated(
    sender, instance, created, *args, **kwargs
):
    if not created:
        async_task(update_child_events_for_master, instance)


@receiver(post_save, sender=models.GamePosting)
def create_player_events_as_needed(sender, instance, created, *args, **kwargs):
    if instance.players.count() > 0:
        async_task(create_game_player_events, instance)


@receiver(post_save, sender=Occurrence)
def create_or_update_player_occurence(sender, instance, created, *args, **kwargs):
    async_task(
        "looking_for_group.games.tasks.create_or_update_linked_occurences_on_edit",
        instance,
        created,
    )


@receiver(m2m_changed, sender=models.GamePosting.players.through)
def sync_calendar_on_player_clear(sender, instance, action, pk_set, *args, **kwargs):
    if action == "post_clear":
        # All players removed, let's clean up the calendars.
        instance.event.get_child_events().delete()
        adhocsessions = instance.gamesession_set.filter(session_type="adhoc")
        if adhocsessions.count() > 0:
            for sess in adhocsessions:
                sess.event.get_child_events().delete()


@receiver(post_save, sender=models.Player)
def sync_calendar_on_player_add(sender, instance, created, *args, **kwargs):
    if created and instance.game.event:
        logger.debug("Syncing calendar for new player")
        async_task(sync_calendar_for_arriving_player, instance)


@receiver(post_save, sender=models.Player)
def update_games_joined(sender, instance, created, *args, **kwargs):
    if created:
        instance.gamer.games_joined = F("games_joined") + 1
        instance.gamer.save()


@receiver(pre_delete, sender=models.Player)
def clear_calendar_on_player_remove(sender, instance, *args, **kwargs):
    async_task(clear_calendar_for_departing_player, instance)


@receiver(player_left)
def update_games_left(sender, player, *args, **kwargs):
    gamer = player.gamer
    gamer.games_left = F("games_left") + 1
    gamer.save()


@receiver(player_kicked)
def update_games_kicked(sender, player, *args, **kwargs):
    gamer = player.gamer
    gamer.games_kicked = F("games_kicked") + 1
    gamer.save()


@receiver(pre_save, sender=models.GameSession)
def generate_master_event_occurrence_for_adhoc_session(
    sender, instance, *args, **kwargs
):
    """
    If an adhoc session, generate or update necessary event.
    """
    if instance.session_type == "adhoc":
        gm_calendar, created = Calendar.objects.get_or_create(
            slug=instance.game.gm.username,
            defaults={"name": "{}'s calendar".format(instance.game.gm.username)},
        )
        if not instance.occurrence:
            logger.debug(
                "No occurrence defined yet, creating a master event for ad hoc session..."
            )
            master_event = models.GameEvent.objects.create(
                start=instance.scheduled_time,
                end=instance.scheduled_time
                + timedelta(minutes=int(instance.game.session_length * 60)),
                title="Ad hoc session for {}".format(instance.game.title),
                description=instance.game.game_description,
                creator=instance.game.gm.user,
                calendar=gm_calendar,
            )
            logger.debug(
                "Master event created with pk of {}! Proceeding to fetch occurrence...".format(
                    master_event.pk
                )
            )
            master_occurrence = master_event.get_occurrences(
                instance.scheduled_time - timedelta(days=5),
                instance.scheduled_time + timedelta(days=60),
            )[0]
            calendar_list = []
            if instance.players_expected.count() > 0:
                logger.debug(
                    "Players are associated with this. Adding any missing child events for adhoc session."
                )
                for player in instance.players_expected.all():
                    c, created = Calendar.objects.get_or_create(
                        slug=player.gamer.username,
                        defaults={
                            "name": "{}'s calendar".format(player.gamer.username)
                        },
                    )
                    calendar_list.append(c)
                master_event.generate_missing_child_events(calendar_list)
            logger.debug("Persisting occurrence...")
            master_occurrence.save()
            logger.debug("Occurence saved with pk of {}".format(master_occurrence.pk))
            instance.occurrence = master_occurrence


@receiver(post_save, sender=models.GameSession)
def check_update_player_calendars_for_adhoc_session(
    sender, instance, created, *args, **kwargs
):
    if instance.session_type == "adhoc":
        async_task(update_player_calendars_for_adhoc_session, instance)


@receiver(m2m_changed, sender=models.GameSession.players_expected.through)
def update_player_calendars_on_player_add(
    sender, instance, action, pk_set, *args, **kwargs
):
    if instance.session_type == "adhoc":
        async_task(update_player_calendars_for_adhoc_session, instance)


@receiver(invite_accepted, sender=Invite)
def process_invite_accepted(sender, invite, acceptor, *args, **kwargs):
    if invite.content_type.name.lower() == "game":
        logger.debug(
            "Invite for game {} accepted. Processing...".format(
                invite.content_object.title
            )
        )
        player, created = models.Player.objects.get_or_create(
            game=invite.content_object, gamer=acceptor.gamerprofile
        )
        if created:
            logger.debug(
                "Player {} added to game {}".format(
                    acceptor.gamerprofile, invite.content_object.title
                )
            )
            notify.send(
                acceptor,
                recipient=invite.creator,
                verb=_(" accepted your invite"),
                target=invite.content_object,
            )
        else:
            logger.debug("Player was already a member of game... moving on.")


@receiver(m2m_changed, sender=models.GamePosting.communities.through)
def fire_new_game_notification_task(
    sender, instance, action, reverse, model, pk_set, *args, **kwargs
):
    if action == "post_add":
        if reverse:
            games = model.objects.filter(id__in=[pk_set])
            comms = [instance]
            for game in games:
                async_task(notify_subscribers_of_new_game, comms, game)
        else:
            comms = models.GamerCommunity.objects.filter(id__in=pk_set)
            game = instance
            async_task(notify_subscribers_of_new_game, comms, game)


@receiver(pre_save, sender=models.GamePosting)
def remove_event_for_cancelled_game(sender, instance, *args, **kwargs):
    """
    If a game is cancelled, check to see if it already had completed game sessions.
    If so, delete the incomplete game sessions and change the end date for the game and game event to now.
    If not, remove the start and end date for the game and remove the event.
    """
    if instance.status == "cancel" and instance.event:
        existing_sessions = models.GameSession.objects.filter(game=instance)
        if existing_sessions.count() > 0:
            with transaction.atomic():
                for session in existing_sessions:
                    if (
                        session.status not in ["complete"]
                        and session.scheduled_time > timezone.now()
                    ):
                        session.delete()
            instance.end_date = timezone.now().date()
            instance.event.end = timezone.now()
            instance.event.save()
        else:
            instance.start_time = None
            instance.end_date = None
            ev = instance.event
            instance.event = None
            async_task(remove_event_and_descendants, ev)
