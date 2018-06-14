import logging
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from ..game_catalog.utils import AbstractUUIDModel
from ..game_catalog.models import PublishedGame, GameSystem
from ..gamer_profiles.models import GamerProfile, GamerCommunity

logger = logging.getLogger("games")

GAME_TYPE_CHOICES = (
    ("oneshot", _("One-Shot")),
    ("shortadv", _("Short Adventure (multiple sessions)")),
    ("campaign", _("Campaign")),
)


GAME_FREQUENCY_CHOICES = (
    ("weekly", _("Every week")),
    ("biweekly", _("Every other week")),
    ("monthly", _("Every month")),
    ("custom", _("Custom: See description for details")),
)


GAME_STATUS_CHOICES = (
    ("open", _("Open")),
    ("started", _("In Progress")),
    ("replace", _("Seeking replacement player")),
    ("cancel", _("Cancelled")),
    ("closed", _("Completed")),
)


# Create your models here.
class Game(TimeStampedModel, AbstractUUIDModel, models.Model):
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
    gm = models.ManyToManyField(GamerProfile, null=True, blank=True)
    max_players = models.PositiveIntegerField(
        default=1,
        help_text=_("Max number of players that will be in the game, excluding GM."),
    )
    game_system = models.ForeignKey(
        GameSystem,
        null=True,
        blank=True,
        help_text=_("What game system will you be using?"),
    )
    published_game = models.ForeignKey(
        PublishedGame,
        null=True,
        blank=True,
        help_text=_("What type of game are you playing, e.g. D&D5E?"),
    )
    game_frequency = models.CharField(
        max_length=15,
        choices=GAME_FREQUENCY_CHOICES,
        default="weekly",
        help_text=_("How often will this be played?"),
        db_index=True,
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

    def __str__(self):
        return "Game: {0} [{1}]".format(self.title, self.id)

    def get_absolute_url(self):
        return reverse("gamerprofile:game_detail", kwargs={"game": self.pk})
