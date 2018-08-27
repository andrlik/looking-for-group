import logging
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from isbn_field import ISBNField
from model_utils.models import TimeStampedModel
from .utils import AbstractTaggedLinkedModel, AbstractUUIDModel


# Create your models here.
logger = logging.getLogger("catalog")


class GamePublisher(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A publisher of games.
    """

    name = models.CharField(max_length=255, db_index=True, help_text=_("Company Name"))
    logo = models.ImageField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, help_text=_("Company URL"))

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:pub_detail", kwargs={"publisher": self.id})

    class Meta:
        ordering = ['name']


class GameSystem(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDModel, models.Model
):
    """
    A root rule system potentially used for multiple games.
    """

    name = models.CharField(
        max_length=100, db_index=True, help_text=_("Name of the game system.")
    )
    description = models.TextField(
        null=True, blank=True, help_text=_("Description of the system.")
    )
    original_publisher = models.ForeignKey(
        GamePublisher,
        help_text=_("Publisher who originally released the rules system."),
        on_delete=models.CASCADE,
    )
    image = models.ImageField(null=True, blank=True)
    isbn = ISBNField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("ISBN of published ruleset if applicable."),
    )
    publication_date = models.DateField(
        null=True, blank=True, help_text=_("Release/publication date of this system.")
    )
    ogl_license = models.BooleanField(
        default=False, help_text=_("Released under an Open Gaming License?")
    )
    system_url = models.URLField(
        null=True, blank=True, help_text=_("More info can be found here.")
    )

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:system_detail", kwargs={"system": self.id})

    class Meta:
        ordering = ['name']


class PublishedGame(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDModel, models.Model
):
    """
    A published game.
    """

    title = models.CharField(
        max_length=150, db_index=True, help_text=_("Title of the game")
    )
    edition = models.CharField(
        max_length=25,
        default="1",
        help_text=_("Common edition name for this version of the game."),
    )
    publisher = models.ForeignKey(
        GamePublisher, help_text=_("Publisher of the game."), on_delete=models.CASCADE
    )
    game_system = models.ForeignKey(
        GameSystem,
        null=True,
        blank=True,
        help_text=_("Rules system the game is based upon."),
        on_delete=models.CASCADE,
    )
    image = models.ImageField(null=True, blank=True)
    description = models.TextField(
        null=True, blank=True, help_text=_("Description of the game.")
    )
    url = models.URLField(
        null=True, blank=True, help_text=_("More info can be found here.")
    )
    isbn = ISBNField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("ISBN of published game if applicable."),
    )
    publication_date = models.DateField(
        null=True, blank=True, help_text=_("Release/publication date of game.")
    )

    def __str__(self):
        return "{0} ({1})".format(self.title, self.edition)  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:game_detail", kwargs={"game": self.id})

    class Meta:
        ordering = ['title', '-publication_date']


class PublishedModule(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDModel, models.Model
):
    """
    A published campaign/adventure module that might be used as the basis for gameplay.
    """

    title = models.CharField(
        max_length=255, db_index=True, help_text=_("Title of module")
    )
    publisher = models.ForeignKey(
        GamePublisher,
        help_text=_(
            "Publisher of module. May be different than original game publisher."
        ),
        on_delete=models.CASCADE,
    )
    isbn = ISBNField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("ISBN of published module if applicable."),
    )
    publication_date = models.DateField(
        null=True, blank=True, help_text=_("Release/publication date for this module.")
    )
    parent_game = models.ForeignKey(
        PublishedGame,
        help_text=_("Module is written for this game."),
        on_delete=models.CASCADE,
    )
    image = models.ImageField(null=True, blank=True)
    url = models.URLField(
        blank=True, null=True, help_text=_("More info can be found here.")
    )

    def __str__(self):
        return "{0} ({1})".format(
            self.title, self.parent_game.title
        )  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:module_detail", kwargs={"module": self.id})

    class Meta:
        ordering = ['title', '-publication_date']
