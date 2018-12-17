import logging
from datetime import timedelta

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models.query_utils import Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from schedule.models import Calendar, Event, EventManager, EventRelation, EventRelationManager, Occurrence, Rule
from schedule.models.calendars import CalendarManager
from schedule.periods import Day, Week

from ..game_catalog.models import GameEdition, GameSystem, PublishedModule
from ..game_catalog.utils import AbstractTaggedLinkedModel, AbstractUUIDWithSlugModel
from ..gamer_profiles.models import GamerCommunity, GamerProfile
from ..invites.models import Invite
from .utils import check_table_exists

logger = logging.getLogger("games")


class CurrentlyBlocked(Exception):
    pass


class GameClosed(Exception):
    pass


class GameEventRelationManager(EventRelationManager):

    # def get_events_for_object(self, content_object, distinction='', inherit=True):
    #     ct = ContentType.objects.get_for_model(content_object)
    #     if distinction:
    #         dist_q = Q(eventrelation__distinction=distinction)
    #         cal_dist_q = Q(calendar__calendarrelation__distinction=distinction)
    #     else:
    #         dist_q = Q()
    #         cal_dist_q = Q()
    #     if inherit:
    #         inherit_q = Q(
    #             cal_dist_q,
    #             calendar__calendarrelation__contenttype=ct,
    #             calendar__calendarrelation__object_id=content_object.id,
    #             calendar__calendarrelation__inheritable=True
    #         )
    #     else:
    #         inherit_q = Q()
    #     event_q = Q(dist_q, eventrelation__content_type=ct, eventrelation__object_id=content_object.id)
    #     return GameEvent.objects.filter(inherit_q | event_q)

    # def create_relation(self, event, content_object, distinction=''):
    #     return GameEventRelation.objects.create(event=event, distinction=distinction, content_object=content_object)

    pass


class AvailableCalendarManager(CalendarManager):
    """
    A manager that enables creating and managing availability calendars for users.
    """

    def get_or_create_availability_calendar_for_gamer(self, gamer):
        """
        For the given gamer, either get or create their availability calendar.
        """
        gamer_primary_calendar, created = Calendar.objects.get_or_create(slug=gamer.username, defaults={'name': "{}'s calendar".format(gamer.username)})
        return self.get_or_create_calendar_for_object(gamer_primary_calendar, distinction='available', name="{} availability".format(gamer.username))

    def find_compatible_schedules(self, requester_calendar, gamer_list):
        """
        For each gamer in the gamer_list queryset, check their availability calendars
        and return a narrowed list that only includes the ones with potentially compatible avaialbility from
        the requestor calendar.

        First we define a Period that represents the next week days. Then we query the avaialbility events from said period in the requestor calendar.
        For each of those occurrences, we check the avaialbility for conflicts. Gamers who have at least one area of acceptable overlap in the period are
        included in the returned list of GamerProfiles.

        This queryset can be subsequently used for filtering game lists, etc.
        """
        end_date_empty_q = Q(rule__isnull=False, end_recurring_period__isnull=True)
        end_date_future_q = Q(end_recurring_period__gt=timezone.now())
        query_range = Week(events=requester_calendar.events.filter(end_date_future_q | end_date_empty_q), date=timezone.now()).next_week()
        requestor_occurrences = query_range.get_occurrences()
        matches = []
        gamer_list_length = gamer_list.count()
        logger.debug("Starting evaluation of {} gamers".format(gamer_list_length))
        for occurrence in requestor_occurrences:
            conflicts = self.check_availability(gamer_list, occurrence.start, occurrence.end, minimum_overlap=150)
            if (conflicts and len(conflicts) < gamer_list_length) or not conflicts:
                logger.debug("There is at least one match here. Adding gamer(s) to match list.")
                match_list = gamer_list.exclude(id__in=[item['gamer'].pk for item in conflicts])
                logger.debug("Appening {} gamers".format(match_list.count()))
                matches.append(match_list)
                gamer_list = gamer_list.filter(id__in=[item['gamer'].pk for item in conflicts])
                gamer_list_length = gamer_list.count()
                logger.debug("New list of gamers to evaluate is {}".format(gamer_list_length))
                if gamer_list_length == 0:
                    break
        logger.debug("{} matches in list".format(len(matches)))
        if len(matches) > 1:
            logger.debug("Executing unions")
            qs1 = matches.pop()
            for item in matches:
                qs1 = qs1.union(item)
            return qs1
        if len(matches) == 1:
            logger.debug("Grabbing queryset")
            return matches[0]
        return matches

    def check_availability(self, gamer_list, start, end, minimum_overlap=None):
        """
        For a given gamer list and two timezone aware datetimes,
        evaluate whether it falls within their availability. Assumes that the whole
        time must fit within the schedule.
        :returns: A list of dicts containing the gamer and the conflict., or any empty list
        if no conflicts.
        """
        conflict_list = []
        matches = 0
        for gamer in gamer_list:
            logger.debug("Evaluating for gamer {}".format(gamer))
            cal = self.get_or_create_availability_calendar_for_gamer(gamer)
            result = cal.check_proposed_time(start, end, minimum_overlap)
            if result:
                logger.debug("Received {} conflicts".format(len(result)))
                conflict_list.append({"gamer": gamer, "conflicts": result})
            else:
                matches += 1
                logger.debug("No conflicts for this gamer. Currently {} matching gamers".format(matches))
        logger.debug("Returning list of {} conflicts".format(len(conflict_list)))
        return conflict_list


class AvailableCalendar(Calendar):
    """
    A proxy model that allows checking for availability conflicts by treating events/occurrences
    as if they represent free time instead of booked time.
    """

    objects = AvailableCalendarManager()

    def check_proposed_time(self, start, end, minimum_overlap=None):
        """
        For two timezone aware datetimes, check if they fall within the availability.
        Return either None or a dict describing the conflict.

        Minimum overlap is either None to represent the whole time must fit within availability, or
        a minumum number of minutes that must overlap to get an appropriate value.
        For most RPGs, that means at least 120-180 minutes must overlap, but when checking for a specific session,
        the default will require it all to fit within.
        """
        logger.debug("Received minimum overlap of {}".format(minimum_overlap))
        if minimum_overlap and end - start > timedelta(seconds=minimum_overlap * 60):
            minimum_overlap = timedelta(seconds=minimum_overlap * 60)
        elif minimum_overlap and end - start < timedelta(seconds=minimum_overlap * 60):
            logger.debug("Time to check is less than specified minimum overlap, so using time to check instead.")
            minimum_overlap = end - start
        else:
            logger.debug("Setting minimum overlap to check period")
            minimum_overlap = end - start
        logger.debug("Minimum overlap is now {}".format(minimum_overlap.seconds))
        end_date_empty_q = Q(rule__isnull=False, end_recurring_period__isnull=True)
        end_date_future_q = Q(end_recurring_period__gt=timezone.now())
        day_period = Day(events=self.events.filter(end_date_empty_q | end_date_future_q), date=start)
        occurrences = day_period.get_occurrences()
        logger.debug("Occurrences fetched.")
        error_reasons = []
        matches = []
        try:
            for occurrence in occurrences:
                logger.debug("Evaluating {} - {} against start: {} and end {}".format(occurrence.start, occurrence.end, start, end))
                if occurrence.start > start and occurrence.end < end and occurrence.end - occurrence.start < minimum_overlap:
                    logger.debug("Occurrence begins after start and ends before end. Overlap is insufficient.")
                    error_reasons.append(occurrence)
                elif occurrence.start <= start and occurrence.end < end and occurrence.end - start < minimum_overlap:
                    logger.debug("Occurrence begins before start, but ends before end. Overlap is insufficient. ")
                    error_reasons.append(occurrence)
                elif occurrence.start > start and occurrence.end >= end and end - occurrence.start < minimum_overlap:
                    logger.debug("Occurrence begins after start but occurrence goes late than end. Overlap is still insufficient")
                    error_reasons.append(occurrence)
                elif occurrence.start <= start and occurrence.end >= end and end - start < minimum_overlap:
                    logger.debug("occurrence is larger than end and start, but the minimum overlap is still too small")
                    error_reasons.append(occurrence)
                else:
                    logger.debug("There is sufficient overlap. This is a MATCH")
                    matches.append(occurrence)
        except StopIteration:
            return ["No availability"]
        if len(matches) > 0:
            logger.debug("Returning None to signify match")
            return None
        else:
            if len(error_reasons) > 0:
                logger.debug("Returning list of conflicts.")
                return error_reasons
            else:
                logger.debug("Returning default value as user has no availability defined for this day.")
                return ["No availability"]

    class Meta:
        proxy = True


class GameEventRelation(EventRelation):
    """
    Override to make sure that we can fetch GameEvent objects.
    """

    objects = GameEventRelationManager()

    class Meta:
        proxy = True


class GameEventManager(EventManager):
    def get_for_object(self, content_object, distinction="", inherit=True):
        return GameEventRelation.objects.get_events_for_object(
            content_object, distinction=distinction, inherit=inherit
        )  # pragma: no cover


class GameEvent(Event):
    """
    Adds the ability to fetch child or master events.
    """

    objects = GameEventManager()

    def get_child_events(self):
        ct = ContentType.objects.get_for_model(self)
        eventrelations = GameEventRelation.objects.filter(
            content_type=ct, object_id=self.id, distinction="playerevent"
        )
        logger.debug("Found {} event relations".format(eventrelations.count()))
        child_events = GameEvent.objects.filter(
            id__in=[er.event.id for er in eventrelations]
        )
        return child_events

    def update_child_events(self):
        existing_events = self.get_child_events()
        logger.debug(
            "Running update for {} child events...".format(existing_events.count())
        )
        updated_rows = existing_events.update(
            start=self.start,
            end=self.end,
            title=self.title,
            description=self.description,
            rule=self.rule,
            end_recurring_period=self.end_recurring_period,
            color_event=self.color_event,
        )
        logger.debug("Updated {} existing child events".format(updated_rows))
        return updated_rows

    def remove_child_events(self):
        return self.get_child_events().delete()

    def generate_missing_child_events(self, calendarlist):
        """
        Check the list of players and for each, evaluate if the event
        already exists in their calendar. If not, create it.
        """
        logger.debug(
            "Starting generation of missing child events for {} calendars...".format(
                len(calendarlist)
            )
        )
        events_added = 0
        existing_events = self.get_child_events()
        logger.debug("Found {} existing child events".format(existing_events.count()))
        if calendarlist:
            for calendar in calendarlist:
                logger.debug("Evaluation calendar for {}".format(calendar.slug))
                user = GamerProfile.objects.get(username=calendar.slug).user
                if not existing_events.filter(calendar=calendar):
                    logger.debug("Event missing from this calendar, creating")
                    with transaction.atomic():
                        logger.debug("Generating child event first...")
                        child_event = type(self).objects.create(
                            start=self.start,
                            end=self.end,
                            title=self.title,
                            description=self.description,
                            creator=user,
                            rule=self.rule,
                            end_recurring_period=self.end_recurring_period,
                            calendar=calendar,
                            color_event=self.color_event,
                        )
                        logger.debug("Created event with pk of {}".format(child_event.pk))
                        logger.debug("Now creating event relation back to master event...")
                        ch_rel = GameEventRelation.objects.create_relation(
                            event=child_event,
                            content_object=self,
                            distinction="playerevent",
                        )
                        logger.debug("Created event relation {} for child event {}".format(ch_rel.pk, child_event.pk))
                        logger.debug(
                            "Added event {} for calendar {}".format(
                                child_event.title, calendar.slug
                            )
                        )
                        events_added += 1
        return events_added

    def delete(self, *args, **kwargs):
        if self.is_master_event:
            self.remove_child_events()
        return super().delete()

    @property
    def child_events(self):
        return self.get_child_events()

    def get_master_event(self):
        ct = ContentType.objects.get_for_model(self)
        try:
            masterevent = EventRelation.objects.get(
                event=self, content_type=ct, distinction="playerevent"
            )
        except ObjectDoesNotExist:
            return False
        return masterevent

    @property
    def master_event(self):
        return self.get_master_event()

    def get_related_game(self):
        if self.is_master_event():
            return GamePosting.objects.get(event=self)
        return GamePosting.objects.get(event=self.get_master_event())

    def is_master_event(self):
        if not self.master_event:
            return True
        return False

    def is_player_event(self):
        if self.is_master_event():
            return False
        return True

    class Meta:
        proxy = True


class ChildOccurenceLink(models.Model):
    """
    An object to help keep a player occurrence linked to the master event occurrence.
    """

    master_event_occurence = models.ForeignKey(
        Occurrence, related_name="child_occurence_link", on_delete=models.CASCADE
    )
    child_event_occurence = models.ForeignKey(
        Occurrence, related_name="master_occurence_link", on_delete=models.CASCADE
    )

    class Meta:
        index_together = ["master_event_occurence", "child_event_occurence"]
        unique_together = ["master_event_occurence", "child_event_occurence"]


def get_rules_as_tuple(*args, **kwargs):
    """
    Lazily extract the rules from the database and provide as a tuple.
    """
    if not check_table_exists("schedule_rule") or Rule.objects.count() == 0:
        return GAME_FREQUENCY_CHOICES  # pragma: no cover
    default_list = [("na", _("Not Applicable")), ("Custom", _("Custom"))]
    result_list = default_list + [
        (i.name, _(i.description))
        for i in Rule.objects.filter(*args, **kwargs).order_by("name")
    ]
    return tuple(result_list)


GAME_TYPE_CHOICES = (
    ("oneshot", _("One-Shot")),
    ("shortadv", _("Short Adventure (multiple sessions)")),
    ("campaign", _("Campaign")),
)


GAME_FREQUENCY_CHOICES = (
    ("weekly", _("Every week")),
    ("biweekly", _("Every other week")),
    ("monthly", _("Every month")),
    ("na", _("N/A")),
    ("custom", _("Custom: See description for details")),
)


GAME_STATUS_CHOICES = [
    ("open", _("Open")),
    ("started", _("In Progress")),
    ("replace", _("Seeking replacement player")),
    ("cancel", _("Cancelled")),
    ("closed", _("Completed")),
]

GAME_PRIVACY_CHOICES = (
    ("private", _("Private Link (unlisted)")),
    ("community", _("Friends/Selected Communities")),
    ("public", _("Public")),
)

CHARACTER_STATUS_CHOICES = (
    ("pending", _("Submitted, pending approval")),
    ("approved", _("Approved")),
    ("rejected", _("Rejected")),
    ("inactive", _("Inactive (or deceased)")),
)

SESSION_STATUS_CHOICES = (
    ("pending", _("Scheduled")),
    ("cancel", _("Cancelled")),
    ("complete", _("Completed")),
)

GAME_APPLICATION_STATUS_CHOICES = (
    ("new", _("Awaiting submission.")),
    ("pending", _("Pending Review")),
    ("deny", _("Denied")),
    ("approve", _("Approved")),
)


SESSION_TYPE_CHOICES = (("normal", "Normal"), ("adhoc", "Ad hoc"))


# Create your models here.
class GamePosting(
    TimeStampedModel, AbstractUUIDWithSlugModel, AbstractTaggedLinkedModel, models.Model
):
    """
    A user-created game.
    """

    game_type = models.CharField(
        max_length=25,
        choices=GAME_TYPE_CHOICES,
        default="oneshot",
        db_index=True,
        help_text=_("Is this a campaign or something shorter?"),
    )
    status = models.CharField(
        max_length=10,
        help_text=_("Current game status"),
        choices=GAME_STATUS_CHOICES,
        db_index=True,
        default="open",
    )
    title = models.CharField(
        max_length=255, help_text=_("What is the title of your campaign/game?")
    )
    gm = models.ForeignKey(
        GamerProfile, null=True, on_delete=models.CASCADE, related_name="gmed_games"
    )
    featured_image = models.ImageField(
        verbose_name=_("Featured image"),
        help_text=_(
            "Featured image for the game to give players a flavor of your game."
        ),
        null=True,
        blank=True,
    )
    featured_image_cw = models.CharField(
        max_length=50,
        verbose_name=_("Featured image content warning"),
        help_text=_(
            "Content warning for featured image, if applicable. If populated, we will hide the featured image behind a warning that users must dismiss."
        ),
        blank=True,
        null=True,
    )
    min_players = models.PositiveIntegerField(
        default=1,
        help_text=_(
            "Minimum number of players needed to schedule this game, excluding the GM."
        ),
    )
    max_players = models.PositiveIntegerField(
        default=3,
        help_text=_("Max number of players that will be in the game, excluding GM."),
    )
    adult_themes = models.BooleanField(
        default=False, help_text=_("Will this contain adult themes?")
    )
    content_warning = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text=_(
            "Please include any content warnings your players should be aware of..."
        ),
    )
    privacy_level = models.CharField(
        max_length=15,
        choices=GAME_PRIVACY_CHOICES,
        db_index=True,
        default="private",
        help_text=_("Choose the privacy level for this posting."),
    )
    game_system = models.ForeignKey(
        GameSystem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("What game system will you be using?"),
    )
    published_game = models.ForeignKey(
        GameEdition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_(
            "What type of game are you playing, e.g. D&D5E? Leave blank for homebrew."
        ),
    )
    published_module = models.ForeignKey(
        PublishedModule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_(
            "Will this game be based on a published module? Leave blank for homebrew."
        ),
    )
    game_frequency = models.CharField(
        max_length=15,
        choices=get_rules_as_tuple(),
        default="na",
        help_text=_("How often will this be played?"),
        db_index=True,
    )
    start_time = models.DateTimeField(
        null=True, blank=True, help_text=_("Date and time of first session.")
    )
    session_length = models.DecimalField(
        verbose_name=_("Length (hours)"),
        decimal_places=2,
        max_digits=4,
        null=True,
        blank=True,
        help_text=_("Your estimate for how long a session will take in hours."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_(
            "What date does this end? (Only used for adventures/campaigns.) You can set this later if you prefer."
        ),
    )
    game_description = models.TextField(
        help_text=_(
            "Description of the game. You can used Markdown for formatting/link."
        )
    )
    game_description_rendered = models.TextField(
        blank=True,
        null=True,
        help_text=_("Automated rendering of markdown text as HTML."),
    )
    communities = models.ManyToManyField(
        GamerCommunity,
        blank=True,
        help_text=_("Which communities would you like to post this in? (Optional)"),
    )
    sessions = models.PositiveIntegerField(default=0)
    players = models.ManyToManyField(GamerProfile, through="Player")
    event = models.ForeignKey(
        GameEvent,
        null=True,
        blank=True,
        related_name="games",
        on_delete=models.SET_NULL,
    )
    invites = GenericRelation(Invite)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse_lazy("games:game_detail", kwargs={"gameid": self.slug})

    def get_player_calendars(self):
        """
        Generates any missing player calendars
        """
        player_calendars = []
        for player in self.players.all():
            calendar, created = Calendar.objects.get_or_create(
                slug=player.username,
                defaults={"name": "{}'s Calendar".format(player.username)},
            )
            player_calendars.append(calendar)
        return player_calendars

    def get_pending_applicant_count(self):
        return GamePostingApplication.objects.filter(
            game=self, status="pending"
        ).count()

    def generate_player_events_from_master_event(self):
        events_generated = 0
        if self.event:
            events_generated = self.event.generate_missing_child_events(
                self.get_player_calendars()
            )
        return events_generated

    def get_next_scheduled_session_occurrence(self):
        """
        Retrieves the next session time (if available)
        """
        if self.event:
            date_cutoff = self.start_time - timedelta(days=1)
            if self.sessions > 0:
                logger.debug("Completed sessions: {}.".format(self.sessions))
                latest_session = self.gamesession_set.filter(
                    status__in=["complete", "cancel"]
                ).latest("scheduled_time")
                date_cutoff = latest_session.scheduled_time + timedelta(days=1)
                logger.debug("Set new date cutoff of {}".format(date_cutoff))
            logger.debug("Checking for occurrences after {}".format(date_cutoff))
            occurrences = self.event.occurrences_after(after=date_cutoff)
            next_occurrence = None
            try:
                next_occurrence = next(occurrences)
                while next_occurrence.start < date_cutoff:
                    next_occurrence = next(occurrences)
                logger.debug(
                    "found next occurrence starting at {}".format(next_occurrence.start)
                )
            except StopIteration:  # pragma: no cover
                pass  # There is no next occurrence.
            return next_occurrence
        return None

    @property
    def next_session_time(self):
        if self.event:
            next_occurrence = self.get_next_scheduled_session_occurrence()
            if next_occurrence:
                return next_occurrence.start
        return None

    def get_next_session(self):
        if self.event:
            sessions_to_check = GameSession.objects.filter(game=self, session_type='normal', status="pending")
            if sessions_to_check.count() > 0:
                return sessions_to_check.earliest("scheduled_time")
        return None

    def create_session_from_occurrence(self, occurrence):
        """
        For a given occurrence, generate the session placeholder.
        Note: this will also persist an occurrence even if it does not already
        exist.
        """
        if not occurrence:
            logger.debug("no occurrence so no session")
            return None
        if occurrence.event.pk == self.event.pk:
            logger.debug("Occurrence is valid; creating session.")
            occurrence.save()
            session, created = GameSession.objects.get_or_create(
                game=self,
                occurrence=occurrence,
                defaults={"status": "pending", "scheduled_time": occurrence.start},
            )
            if created:
                logger.debug("Created new session with slug {}".format(session.slug))
                # By default, assume all players are expected.
                logger.debug("Appending players to session record...")
                players = Player.objects.filter(game=self)
                if players.count() > 0:
                    if players.count() == 1:
                        logger.debug("Only one player expected, adding.")
                        session.players_expected.add(players[0])
                    else:
                        logger.debug("Adding multiple players.")
                        session.players_expected.add(*list(players))
                else:
                    logger.debug("No players found.")
            else:
                logger.debug("This is the same occurrence as the last one. Skipping.")
        else:
            raise ValueError(
                "You can only tie a session to an occurrence from the same game."
            )
        return session

    def create_next_session(self):
        return self.create_session_from_occurrence(
            self.get_next_scheduled_session_occurrence()
        )

    def update_completed_session_count(self):
        self.sessions = GameSession.objects.filter(status="complete", game=self).count()
        self.save()

    def delete(self, *args, **kwargs):
        if self.event:
            self.event.delete()
        return super().delete(*args, **kwargs)

    class Meta:
        ordering = ["status", "start_time", "-end_date", "-created"]
        verbose_name = "Game"
        verbose_name_plural = "Games"


class GamePostingApplication(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    An application for a game.
    """

    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    gamer = models.ForeignKey(GamerProfile, on_delete=models.CASCADE)
    message = models.TextField(
        help_text=_("Please include a message with your application.")
    )
    status = models.CharField(
        max_length=15,
        choices=GAME_APPLICATION_STATUS_CHOICES,
        db_index=True,
        default="new",
    )

    def __str__(self):
        return "Application to {} from {}".format(self.game.title, self.gamer.username)

    def get_absolute_url(self):
        return reverse_lazy(
            "games:game_apply_detail", kwargs={"application": self.slug}
        )

    def submit_application(self):
        if self.game.status not in ["open", "replace"]:
            raise GameClosed(
                _("This game is currently closed and not accepting additional players.")
            )
        if self.gamer.user.has_perm("games.can_apply", self.game):
            self.status = "pending"
            self.save()
            return True
        else:
            raise CurrentlyBlocked(
                _("You are currently blocked by the GM from joining this game.")
            )
        return False


class Player(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    An abstract link to a game.
    """

    gamer = models.ForeignKey(GamerProfile, null=True, on_delete=models.SET_NULL)
    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    sessions_expected = models.PositiveIntegerField(default=0)
    sessions_missed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.gamer)

    def get_attendance_rating_for_game(self):
        if self.game.sessions > 0 and self.sessions_expected > 0:
            return (1 - (float(self.sessions_missed) / float(self.sessions_expected))) * 100
        return None

    def get_attendance_average(self):
        """
        Convenience function to fetch the overall attendance average for the gamer.
        """
        return self.gamer.attendance_record

    @property
    def current_character(self):
        characters = Character.objects.filter(
            status__in=["pending", "approved"], player=self
        )
        if characters.count() > 0:
            return characters[0]
        return None


class Character(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    Represents a character being played for a given game.
    """

    name = models.CharField(
        max_length=100, help_text=_("What is this character's name?")
    )
    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_('A brief description of this character, e.g. "Half-elf monk"'),
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=15, choices=CHARACTER_STATUS_CHOICES, default="pending"
    )
    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    sheet = models.FileField(
        help_text=_("Upload your character sheet here."), null=True, blank=True
    )

    def __str__(self):
        return "{0} ({1})".format(self.name, self.player.gamer.username)

    def get_absolute_url(self):
        return reverse_lazy("games:character_detail", kwargs={"character": self.slug})


class GameSession(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    An instance of a posted game. Only generated once played.
    """

    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    session_type = models.CharField(
        max_length=20, choices=SESSION_TYPE_CHOICES, default="normal", db_index=True
    )
    scheduled_time = models.DateTimeField()
    status = models.CharField(
        max_length=15, choices=SESSION_STATUS_CHOICES, default="pending", db_index=True
    )

    players_expected = models.ManyToManyField(
        Player, help_text=_("Players who should be in attendance?")
    )
    players_missing = models.ManyToManyField(
        Player,
        related_name="missed_sessions",
        help_text=_(
            "Are there any players missing here for reasons that don't have to do with the story?"
        ),
    )
    gm_notes = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "Any notes you would like to make here. Markdown can be used for formatting."
        ),
    )
    gm_notes_rendered = models.TextField(null=True, blank=True)
    occurrence = models.ForeignKey(
        Occurrence, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return "{} (session at {})".format(self.game.title, self.scheduled_time.strftime("%Y-%m-%d %H:%M %Z"))

    @property
    def title(self):
        return self.game.title

    def get_absolute_url(self):
        return reverse_lazy("games:session_detail", kwargs={"session": self.slug})

    def move(self, new_schedule_time):
        """
        Reschedule the session in question.
        """
        with transaction.atomic():
            self.scheduled_time = new_schedule_time
            logger.debug("Moving occurrence...")
            if self.occurrence:
                self.occurrence.move(
                    new_schedule_time,
                    new_schedule_time
                    + timedelta(minutes=int(60 * self.game.session_length)),
                )
            logger.debug("Saving self...")
            self.save()

    def get_players_present(self):
        return self.players_expected.exclude(id__in=[m.id for m in self.players_missing.all()])

    def delete(self, *args, **kwargs):
        if self.occurrence:
            self.occurrence.delete()
        return super().delete(*args, **kwargs)

    def cancel(self):
        """
        Cancel this session and the related occurrence.
        """
        with transaction.atomic():
            self.status = "cancel"
            self.occurrence.cancel()
            self.save()

    def uncancel(self):
        """
        Undo an erroneous cancel.
        """
        with transaction.atomic():
            self.status = "pending"
            self.occurrence.uncancel()
            self.save()


class AdventureLog(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    Represents an optional player-visible adventure log for a session.
    This can be created at any time after the initial session is instantiated, provided that it is not in status cancelled.
    """

    session = models.OneToOneField(GameSession, on_delete=models.CASCADE)
    initial_author = models.ForeignKey(
        GamerProfile, null=True, blank=True, on_delete=models.SET_NULL
    )
    title = models.CharField(
        max_length=250, help_text=_("A good headline for this session.")
    )
    body = models.TextField(
        blank=True,
        null=True,
        help_text=_(
            "What happened during this session? (You can use Markdown for formatting/links.)"
        ),
    )
    body_rendered = models.TextField(blank=True, null=True)
    last_edited_by = models.ForeignKey(
        GamerProfile,
        null=True,
        blank=True,
        related_name="latest_editor_logs",
        on_delete=models.SET_NULL,
    )
