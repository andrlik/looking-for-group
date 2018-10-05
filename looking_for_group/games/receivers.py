import logging
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver
from django_q.tasks import async_task
from markdown import markdown
from schedule.models import Calendar, Occurrence, Rule

from . import models
from .tasks import (
    calculate_player_attendance,
    clear_calendar_for_departing_player,
    create_game_player_events,
    create_or_update_linked_occurences_on_edit,
    sync_calendar_for_arriving_player,
    update_child_events_for_master
)

logger = logging.getLogger("games")


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
    if instance.status == 'complete':
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
                    minutes=(60 * instance.session_length)
            ):
                instance.event.end = instance.start_time + timedelta(
                    minutes=(60 * instance.session_length)
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
                    "Created new calendar for user {}".format(instance.gm.username)
                )
            rule = None
            if frequency:
                rule = Rule.objects.get(name=frequency)
            instance.event = models.GameEvent.objects.create(
                start=instance.start_time,
                end=(
                    instance.start_time
                    + timedelta(minutes=(60 * instance.session_length))
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


@receiver(post_save, sender=models.GameEvent)
def update_child_events_when_master_event_updated(
    sender, instance, created, *args, **kwargs
):
    async_task(update_child_events_for_master, instance)


@receiver(post_save, sender=models.GamePosting)
def create_player_events_as_needed(sender, instance, created, *args, **kwargs):
    async_task(create_game_player_events, instance)


@receiver(post_save, sender=Occurrence)
def create_or_update_player_occurence(sender, instance, created, *args, **kwargs):
    async_task(create_or_update_linked_occurences_on_edit, instance, created)


@receiver(m2m_changed, sender=models.GamePosting.players.through)
def sync_calendar_on_player_clear(sender, instance, action, pk_set, *args, **kwargs):
    if action == "post_clear":
        # All players removed, let's clean up the calendars.
        instance.event.get_child_events().delete()


@receiver(post_save, sender=models.Player)
def sync_calendar_on_player_add(sender, instance, created, *args, **kwargs):
    if created and instance.game.event:
        logger.debug("Syncing calendar for new player")
        async_task(sync_calendar_for_arriving_player, instance)


@receiver(post_delete, sender=models.Player)
def clear_calendar_on_player_remove(sender, instance, *args, **kwargs):
    async_task(clear_calendar_for_departing_player, instance)
