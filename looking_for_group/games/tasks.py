import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from schedule.models import Calendar, Occurrence

from . import models

logger = logging.getLogger("games")


def update_child_events_for_master(event):
    if event.is_master_event() and event.child_events.count() > 0:
        event.update_child_events()


def create_game_player_events(gameposting):
    if gameposting.event and gameposting.players.count() > 0:
        gameposting.generate_player_events_from_master_event()


def create_or_update_linked_occurences_on_edit(occurence, created=False):
    game_event = models.GameEvent.objects.get(id=occurence.event.id)
    if game_event.is_master_event():
        # Check to ensure this is related to a game posting.
        # This is a game and we need to make sure the players have the event.
        # First, we retrive any existing links.
        logger.debug("This is an master event occurrence linked to a game.")
        child_occurences_to_update = None
        with transaction.atomic():
            if not created:
                logger.debug(
                    "This is an updated occurrence, checking for exising child occurences..."
                )
                polinks = models.ChildOccurenceLink.objects.filter(
                    master_event_occurence=occurence
                )
                logger.debug(
                    "Found {} existing occurences to update.".format(
                        polinks.count()
                    )
                )
                child_occurences_to_update = Occurrence.objects.filter(
                    id__in=[p.child_event_occurence.id for p in polinks]
                )
                updated_records = child_occurences_to_update.update(
                    title=occurence.title,
                    description=occurence.description,
                    start=occurence.start,
                    end=occurence.end,
                    cancelled=occurence.cancelled,
                    original_start=occurence.original_start,
                    original_end=occurence.original_end,
                )
                logger.debug(
                    "Updated {} records requiring changes.".format(updated_records)
                )
            logger.debug("Adding any missing occurences...")
            child_events = game_event.get_child_events()
            if child_occurences_to_update:
                child_events = child_events.exclude(id__in=[c.event.id for c in child_occurences_to_update])
            occ_created = 0
            for event in child_events:
                with transaction.atomic():
                    child_occurence = Occurrence.objects.create(
                        event=event,
                        title=occurence.title,
                        description=occurence.description,
                        start=occurence.start,
                        end=occurence.end,
                        cancelled=occurence.cancelled,
                        original_start=occurence.original_start,
                        original_end=occurence.original_end,
                    )
                    models.ChildOccurenceLink.objects.create(
                        master_event_occurence=occurence,
                        child_event_occurence=child_occurence,
                    )
                    occ_created += 1
            logger.debug("Created {} new linked occurences.".format(occ_created))


def sync_calendar_for_arriving_player(player):
    with transaction.atomic():
        events_created = player.game.generate_player_events_from_master_event()
        logger.debug("Created {} child events.".format(events_created))
        player_event = player.game.event.get_child_events().filter(
            calendar__slug=player.gamer.username
        )[0]
        occurences_to_sync = player.game.event.occurrence_set.filter(
            start__gte=timezone.now()
        )
        if occurences_to_sync.count() > 0:
            logger.debug("Preparing to sync occurences.")
            synced_occurences = 0
            for occ in occurences_to_sync:
                with transaction.atomic():
                    pocc = Occurrence.objects.create(
                        event=player_event,
                        title=occ.title,
                        description=occ.description,
                        start=occ.start,
                        end=occ.end,
                        cancelled=occ.cancelled,
                        original_start=occ.original_start,
                        original_end=occ.original_end,
                    )
                    models.ChildOccurenceLink.objects.create(
                        master_event_occurence=occ, child_event_occurence=pocc
                    )
                    synced_occurences += 1
            logger.debug("Synced {} occurences.".format(synced_occurences))


def clear_calendar_for_departing_player(player):

    try:
        logger.debug("trying to fetch calendar for departing player.")
        player_calendar = Calendar.objects.get(slug=player.gamer.username)

    except ObjectDoesNotExist:  # pragma: no cover
        logger.debug("Calendar does not exist!")
        pass  # No need to delete anything.
    logger.debug("Found calendar!")
    if player.game.event:
        candidate_events = player.game.event.get_child_events().filter(
            calendar=player_calendar
        )
        if candidate_events.count() == 1:
            logger.debug(
                "Player leaving game has a child event, doing a cascade delete."
            )
            candidate_events[0].delete()
        elif candidate_events.count() > 1:  # pragma: no cover
            logger.debug(
                "Player has more than 1 child event here. Something is very wrong but deleting anyway."
            )
            candidate_events.delete()
        else:
            logger.debug("No events to delete.")
    logger.debug("Checking for ad hoc sessions")
    adhocsessions = player.game.gamesession_set.filter(session_type='adhoc').prefetch_related('players_expected')
    if adhocsessions.count() > 0:
        for sess in adhocsessions:
            mevent = models.GameEvent.objects.get(id=sess.occurrence.event.id)
            candidate_events = mevent.get_child_events().filter(calendar=player_calendar)
            if candidate_events.count() > 0:
                logger.debug("Removing an adhoc child event.")
                candidate_events.delete()


def calculate_player_attendance(gamesession):
    """
    Takes all the players that were expected at the game session and
    recalculates their attendance.
    """
    game_players = gamesession.players_expected.all()
    if game_players:
        for player in game_players:
            player.sessions_expected = player.gamesession_set.filter(status='complete').count()
            player.sessions_missed = player.missed_sessions.filter(status='complete').count()
            player.save()


def update_player_calendars_for_adhoc_session(gamesession):
    """
    For all players expected for a given ad hoc session, add or update the events
    on their calendar as needed. If not in the expected list, remove the related event.

    :param gamesession: The :class:`looking_for_group.games.models.GameSession` that is the basis for updating.
    :returns: two ints -- number of created child events, number of deleted child events
    :raises: ValueError
    """
    if gamesession.session_type != "adhoc":
        raise ValueError("This method may only be used for ad hoc sessions!")
    # First we check for any players expected. If a related event does not exist, create it.
    calendar_list = []
    created = 0
    deleted = 0
    with transaction.atomic():
        logger.debug("Checking for players associated with this session...")
        master_event = models.GameEvent.objects.get(pk=gamesession.occurrence.event.pk)
        if gamesession.players_expected.count() > 0:
            logger.debug("This session has players, grabbing calendars")
            for player in gamesession.players_expected.all():
                pcal, created = Calendar.objects.get_or_create(slug=player.gamer.username, defaults={'name': "{}'s calendar".format(player.gamer.username)})  # Create event if missing.
                calendar_list.append(pcal)
            logger.debug("Running generation for {} calendars".format(len(calendar_list)))
            master_event.generate_missing_child_events(calendar_list)
            created = len(calendar_list)
        logger.debug("Checking for missing players...")
        if gamesession.players_expected.count() < gamesession.game.players.count():
            logger.debug("We do have players not associated with this session, grabbing their usernames.")
            non_attending_player_usernames = [np.gamer.username for np in models.Player.objects.filter(game=gamesession.game).exclude(
                id__in=[p.id for p in gamesession.players_expected.all()]
            )]
            logger.debug("Found {} usernames for clearing of child events".format(len(non_attending_player_usernames)))
            if master_event.get_child_events().count() > 0:
                logger.debug("Fetching child events for session...")
                for child_event in master_event.get_child_events():
                    if child_event.calendar.slug in non_attending_player_usernames:
                        logger.debug("Child event is for a non-participating player, removing this from their calendar.")
                        child_event.delete()
                        deleted += 1
    logger.debug("Created {} new child events and deleted {} child events".format(created, deleted))
    return created, deleted


def clean_expired_availability_events():
    avail_calls = models.AvailableCalendar.objects.all()
    deleted_count = 0
    for acal in avail_calls:
        deleted_info = acal.events.filter(end_recurring_period__lt=timezone.now()).delete()
        deleted_count += deleted_info[0]
    logger.info("Deleted {} expired availability events".format(deleted_count))
