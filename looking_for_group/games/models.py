import logging
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from schedule.models import Event, EventManager, Occurrence, Rule, EventRelation, EventRelationManager, Calendar
from ..game_catalog.utils import AbstractUUIDModel
from ..game_catalog.models import PublishedGame, GameSystem, PublishedModule
from ..gamer_profiles.models import GamerProfile, GamerCommunity
from .utils import check_table_exists


logger = logging.getLogger("games")


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

    def get_for_object(self, content_object, distinction='', inherit=True):
        return GameEventRelation.objects.get_events_for_object(content_object, distinction=distinction, inherit=inherit)  # pragma: no cover


class GameEvent(Event):
    """
    Adds the ability to fetch child or master events.
    """

    objects = GameEventManager()

    def get_child_events(self):
        ct = ContentType.objects.get_for_model(self)
        eventrelations = GameEventRelation.objects.filter(content_type=ct, object_id=self.id, distinction='playerevent')
        logger.debug("Found {} event relations".format(eventrelations.count()))
        child_events = GameEvent.objects.filter(id__in=[er.event.id for er in eventrelations])
        return child_events

    def generate_or_update_child_events(self, playerlist):
        '''
        Generate any missing player events and then run a bulk SQL update.
        '''
        with transaction.atomic():
            logger.debug("Checking for missing player events.")
            events_added = self.generate_missing_child_events(self.get_player_calendars())
            logger.debug("Added {} missing events.".format(events_added))
            self.update_child_events()

    def update_child_events(self):
        existing_events = self.get_child_events()
        logger.debug("Running update for {} child events...".format(existing_events.count()))
        updated_rows = existing_events.update(start=self.start, end=self.end, title=self.title, description=self.description, rule=self.rule, end_recurring_period=self.end_recurring_period, color_event=self.color_event)
        logger.debug("Updated {} existing child events".format(updated_rows))
        return updated_rows

    def remove_child_events(self):
        return self.get_child_events().delete()

    def get_player_calendars(self, playerlist):
        '''
        Generates any missing player calendars
        '''
        player_calendars = []
        for player in playerlist:
            calendar, created = Calendar.objects.get_or_create(slug=player.gamer.username, defaults={"name": "{}'s Calendar".format(player.gamer.username)})
            player_calendars.append(player_calendars)
        return player_calendars

    def generate_missing_child_events(self, calendarlist):
        '''
        Check the list of players and for each, evaluate if the event
        already exists in their calendar. If not, create it.
        '''
        logger.debug("Starting generation of missing child events for {} calendars...".format(len(calendarlist)))
        events_added = 0
        existing_events = self.get_child_events()
        logger.debug("Found {} existing child events".format(existing_events.count()))
        if calendarlist:
            for calendar in calendarlist:
                user = GamerProfile.objects.get(username=calendar.slug).user
                if not existing_events.filter(calendar=calendar):
                    logger.debug("Event missing from this calendar, creating")
                    with transaction.atomic():
                        child_event = type(self).objects.create(start=self.start, end=self.end, title=self.title, description=self.description, creator=user, rule=self.rule, end_recurring_period=self.end_recurring_period, calendar=calendar, color_event=self.color_event)
                        GameEventRelation.objects.create_relation(event=child_event, content_object=self, distinction='playerevent')
                        logger.debug("Added event {} for calendar {}".format(child_event.title, calendar.slug))
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
            masterevent = EventRelation.objects.filter(event=self, content_type=ct, distinction='playerevent')
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


def get_rules_as_tuple(*args, **kwargs):
    """
    Lazily extract the rules from the database and provide as a tuple.
    """
    if not check_table_exists("schedule_rule") or Rule.objects.count() == 0:
        return GAME_FREQUENCY_CHOICES
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
    ("private", _("Only someone I explicitly share the link with can join.")),
    (
        "community",
        _(
            "My friends and communities where I have posted this can see and join this game."
        ),
    ),
    ("public", _("Anyone can see this posting and apply to join.")),
)

CHARACTER_STATUS_CHOICES = (
    ("pending", _("Submitted, pending approval")),
    ("approved", _("Approved")),
    ("rejected", _("Rejected")),
    ("inactive", _("Inactive (or deceased)")),
)

SESSION_STATUS_CHOICES = (
    ("pending", _("Scheduled")),
    ("cancel"),
    _("Cancelled"),
    ("complete", _("Completed")),
)


# Create your models here.
class GamePosting(TimeStampedModel, AbstractUUIDModel, models.Model):
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
        PublishedGame,
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
    game_description = models.TextField(
        blank=True, null=True, help_text=_("Description of the game.")
    )
    game_description_rendered = models.TextField(
        blank=True,
        null=True,
        help_text=_("Automated rendering of markdown text as HTML."),
    )
    communities = models.ManyToManyField(GamerCommunity)
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
        return reverse("games:game-posting-detail", kwargs={"game": self.pk})


class Player(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    An abstract link to a game.
    """

    gamer = models.ForeignKey(GamerProfile, null=True, on_delete=models.SET_NULL)
    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    sessions_attended = models.PositiveIntegerField(default=0)
    sessions_missed = models.PositiveIntegerField(default=0)

    def get_attendance_rating_for_game(self):
        if self.game.sessions > 0:
            return float(self.sessions_attended) / float(self.get_sessions_missed)
        return None

    def get_attendance_average(self):
        """
        Convenience function to fetch the overall attendance average for the gamer.
        """
        return self.gamer.attendance_record


class Character(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Represents a character being played for a given game.
    """

    name = models.CharField(
        max_length=100, help_text=_("What is this character's name?")
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=15, choices=CHARACTER_STATUS_CHOICES, default="pending"
    )
    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    sheet = models.FileField(help_text=_("Upload your character sheet here."))

    def __str__(self):
        return "{0} ({1})".format(self.name, self.player.gamer.display_name)


class GameSession(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    An instance of a posted game. Only generated once played.
    """

    game = models.ForeignKey(GamePosting, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()
    status = (
        models.CharField(
            max_length=15,
            choices=SESSION_STATUS_CHOICES,
            default="pending",
            db_index=True,
        ),
    )
    players_present = models.ManyToManyField(
        Player, help_text=_("Players in attendance?")
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
