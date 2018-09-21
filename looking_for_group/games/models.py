import logging
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from schedule.models import Event, Occurrence, Rule
from ..game_catalog.utils import AbstractUUIDModel
from ..game_catalog.models import PublishedGame, GameSystem, PublishedModule
from ..gamer_profiles.models import GamerProfile, GamerCommunity


logger = logging.getLogger("games")


def get_rules_as_tuple(*args, **kwargs):
    """
    Lazily extract the rules from the database and provide as a tuple.
    """
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
    mix_players = models.PositiveIntegerField(
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
        Event, null=True, blank=True, related_name="games", on_delete=models.SET_NULL
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
