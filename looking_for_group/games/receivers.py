import logging
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_q.tasks import async_task
from markdown import markdown
from notifications.signals import notify
from schedule.models import Calendar, Occurrence, Rule

from . import models
from ..invites.signals import invite_accepted
from .tasks import (
    calculate_player_attendance,
    clear_calendar_for_departing_player,
    create_game_player_events,
    create_or_update_linked_occurences_on_edit,
    sync_calendar_for_arriving_player,
    update_child_events_for_master,
    update_player_calendars_for_adhoc_session
)

logger = logging.getLogger("games")


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


@receiver(pre_save, sender=models.AdventureLog)
def render_markdown_log_body(sender, instance, *args, **kwargs):
    if instance.body:
        instance.body_rendered = markdown(instance.body)
    else:
        instance.body_rendered = None


@receiver(post_save, sender=models.GameSession)
def update_complete_session_count(sender, instance, *args, **kwargs):
    if instance.status == "complete":
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
            event_to_kill = instance.event
            instance.event = None
            event_to_kill.delete()


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
    async_task(create_or_update_linked_occurences_on_edit, instance, created)


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


@receiver(post_delete, sender=models.Player)
def update_games_left(sender, instance, *args, **kwargs):
    gamer = instance.gamer
    gamer.games_left = F("games_left") + 1
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
                + timedelta(minutes=instance.game.session_length * 60),
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


@receiver(invite_accepted)
def process_invite_accepted(sender, invite, acceptor, *args, **kwargs):
    if invite.content_type.name == "gameposting":
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
