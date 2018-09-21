import logging
from datetime import timedelta
from markdown import markdown
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from schedule.models import Rule, Event, Calendar
from . import models

logger = logging.getLogger('games')


@receiver(pre_save, sender=models.GamePosting)
def render_markdown_description(sender, instance, *args, **kwargs):
    if instance.description:
        instance.description_rendered = markdown(instance.description)
    else:
        instance.description_rendered = None


@receiver(pre_save, sender=models.GameSession)
def render_markdown_notes(sender, instance, *args, **kwargs):
    if instance.gm_notes:
        instance.gm_notes_rendered = markdown(instance.gm_notes)
    else:
        instance.gm_notes_rendered = None


@receiver(post_save, sender=models.GameSession)
def calculate_attendance(sender, instance, created, *args, **kwargs):
    pass


@receiver(pre_save, sender=models.GamePosting)
def create_update_event_for_game(sender, instance, *args, **kwargs):
    '''
    If the game has enough information to generate an event, check if one already exists and link to it.
    '''
    if instance.start_date and instance.session_length and instance.game_frequency not in ('na', 'Custom'):
        logger.debug("Game posting has enough data to have a corresponding event.")
        if instance.event:
            logger.debug("Event already exists. Reviewing to see if changes are required...")
            needs_edit = False
            if instance.start_date and instance.session_length and instance.game_frequency not in ('na', 'Custom'):
                if instance.start_time != instance.event.start:
                    needs_edit = True
                    logger.debug("Updating start time to {}".format(instance.start))
                    instance.event.start = instance.start_time
                if instance.event.end != instance.start_time + timedelta(minutes=(60 * instance.session_length)):
                    instance.event.end = instance.start_time + timedelta(minutes=(60 * instance.session_length))
                    logger.debug("Updating end time to {}".format(instance.event.end))
                    needs_edit = True
                try:
                    rrule = Rule.objects.get(name=instance.game_frequency)
                    if instance.event.rule != rrule:
                        needs_edit = True
                        instance.event.rule = rrule
                        logger.debug("Updating rule to {}".format(rrule.name))
                except ObjectDoesNotExist:
                    # Something is very wrong here.
                    raise ValueError("Invalid frequency type!")
            if needs_edit:
                logger.debug("Changes were made, saving.")
                instance.event.save()
            else:
                logger.debug("No changes required.")
        else:
            logger.debug("Event does not exist yet. Creating and adding to GM's calendar.")
            calendar, created = Calendar.objects.get_or_create(slug=instance.gm.username, defaults={'name': "{}'s Calendar".format(instance.gm.username)})
            if created:
                logger.debug("Created new calendar for user {}".format(instance.gm.username))
            instance.event = Event.objects.create(start=instance.start_time, end=(instance.start_time + timedelta(minutes=(60 * instance.session_length))), title=instance.name, description=instance.description, creator=instance.gm, rule=Rule.objects.get(name=instance.game_frequency), calendar=calendar)
    else:
        logger.debug("Insufficient data for an event.")
        if instance.event:
            logger.debug("There is an event associated with this. Deleting it.")
            event_to_kill = instance.event
            instance.event = None
            event_to_kill.delete()
