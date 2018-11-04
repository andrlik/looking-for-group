import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from schedule.models import Calendar, Event, EventManager, EventRelation, EventRelationManager, Occurrence, Rule

from ..game_catalog.models import GameSystem, PublishedGame, PublishedModule, GameEdition
from ..game_catalog.utils import AbstractUUIDWithSlugModel
from ..gamer_profiles.models import GamerCommunity, GamerProfile
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
                user = GamerProfile.objects.get(username=calendar.slug).user
                if not existing_events.filter(calendar=calendar):
                    logger.debug("Event missing from this calendar, creating")
                    with transaction.atomic():
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
                        GameEventRelation.objects.create_relation(
                            event=child_event,
                            content_object=self,
                            distinction="playerevent",
                        )
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
            masterevent = EventRelation.objects.filter(
                event=self, content_type=ct, distinction="playerevent"
            )
        except ObjectDoesNotExist:
            return False
        return masterevent

    @property
    def master_event(self):
        return self.get_master_event()

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


GAME_STATUS_CHOICES = (
    ("open", _("Open")),
    ("started", _("In Progress")),
    ("replace", _("Seeking replacement player")),
    ("cancel", _("Cancelled")),
    ("closed", _("Completed")),
)

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


# Create your models here.
class GamePosting(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
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
    min_players = models.PositiveIntegerField(
        default=3,
        help_text=_(
            "Minimum number of players needed to schedule this game, excluding the GM."
        ),
    )
    max_players = models.PositiveIntegerField(
        default=1,
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
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "What date does this end? (Only used for adventures/campaigns.) You can set this later if you prefer."
        ),
    )
    game_description = models.TextField(help_text=_("Description of the game."))
    game_description_rendered = models.TextField(
        blank=True,
        null=True,
        help_text=_("Automated rendering of markdown text as HTML."),
    )
    communities = models.ManyToManyField(GamerCommunity, help_text=_('Which communities would you like to post this in? (Optional)'))
    sessions = models.PositiveIntegerField(default=0)
    players = models.ManyToManyField(GamerProfile, through="Player")
    event = models.ForeignKey(
        GameEvent,
        null=True,
        blank=True,
        related_name="games",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return "Game: {0} [{1}]".format(self.title, self.id)

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

    @property
    def next_session(self):
        if self.event:
            try:
                session = GameSession.objects.get(
                    game=self, occurrence=self.get_next_scheduled_session_occurrence()
                )
            except ObjectDoesNotExist:
                return None
            return session
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

    class Meta:
        ordering = ["status", "start_time", "-end_date", "-created"]


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

    def get_attendance_rating_for_game(self):
        if self.game.sessions > 0 and self.sessions_expected > 0:
            return 1 - (float(self.sessions_missed) / float(self.sessions_expected))
        return None

    def get_attendance_average(self):
        """
        Convenience function to fetch the overall attendance average for the gamer.
        """
        return self.gamer.attendance_record

    @property
    def current_character(self):
        characters = Character.objects.filter(status__in=['pending', 'approved'], player=self)
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
        return "{0} ({1})".format(self.name, self.player.gamer.display_name)

    def get_absolute_url(self):
        return reverse_lazy("games:character_detail", kwargs={"character": self.slug})


class GameSession(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    An instance of a posted game. Only generated once played.
    """

    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
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

    def get_absolute_url(self):
        return reverse_lazy("games:session_detail", kwargs={"session": self.slug})

    def move(self, new_schedule_time):
        """
        Reschedule the session in question.
        """
        with transaction.atomic():
            self.scheduled_time = new_schedule_time
            if self.occurrence:
                self.occurrence.move(
                    new_schedule_time,
                    new_schedule_time
                    + timedelta(minutes=int(60 * self.game.session_length)),
                )
            self.save()

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
