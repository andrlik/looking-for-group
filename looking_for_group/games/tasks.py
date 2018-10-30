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
        try:
            game = models.GamePosting.objects.get(event=game_event)
        except ObjectDoesNotExist:  # pragma: no cover
            return
        if game.players.count() > 0:
            # This is a game and we need to make sure the players have the event.
            # First, we retrive any existing links.
            logger.debug("This is an master event occurrence linked to a game.")
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
                child_events = game_event.get_child_events().exclude(id__in=[c.event.id for c in child_occurences_to_update])
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
        player_event = player.game.event.get_child_events().filter(calendar__slug=player.gamer.username)[0]
        occurences_to_sync = player.game.event.occurrence_set.filter(start__gte=timezone.now())
        if occurences_to_sync.count() > 0:
            logger.debug("Preparing to sync occurences.")
            synced_occurences = 0
            for occ in occurences_to_sync:
                with transaction.atomic():
                    pocc = Occurrence.objects.create(event=player_event, title=occ.title, description=occ.description, start=occ.start, end=occ.end, cancelled=occ.cancelled, original_start=occ.original_start, original_end=occ.original_end)
                    models.ChildOccurenceLink.objects.create(master_event_occurence=occ, child_event_occurence=pocc)
                    synced_occurences += 1
            logger.debug("Synced {} occurences.".format(synced_occurences))


def clear_calendar_for_departing_player(player):

    try:
        player_calendar = Calendar.objects.get(slug=player.gamer.username)
    except ObjectDoesNotExist:  # pragma: no cover
        pass  # No need to delete anything.
    if player.game.event:
        candidate_events = player.game.event.get_child_events().filter(calendar=player_calendar)
        if candidate_events.count() == 1:
            logger.debug("Player leaving game has a child event, doing a cascade delete.")
            candidate_events[0].delete()
        elif candidate_events.count() > 1:  # pragma: no cover
            logger.debug("Player has more than 1 child event here. Something is very wrong but deleting anyway.")
            candidate_events.delete()
        else:
            logger.debug("No events to delete.")


def calculate_player_attendance(gamesession):
    '''
    Takes all the players that were expected at the game session and
    recalculates their attendance.
    '''
    game_players = gamesession.players_expected.all()
    if game_players:
        for player in game_players:
            player.sessions_expected = player.gamesession_set.count()
            player.sessions_missed = player.missed_sessions.count()
            player.save()
