import logging

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from isbn_field import ISBNField
from model_utils.models import TimeStampedModel

from .utils import AbstractTaggedLinkedModel, AbstractUUIDModel, AbstractUUIDWithSlugModel

# Create your models here.
logger = logging.getLogger("catalog")


class GamePublisher(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A publisher of games.
    """

    name = models.CharField(max_length=255, db_index=True, help_text=_("Company Name"))
    logo = models.ImageField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, help_text=_("Company URL"))
    description = models.TextField(null=True, blank=True, help_text=_("Description of the publisher."))

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:pub-detail", kwargs={"publisher": self.id})

    class Meta:
        ordering = ["name"]


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
    description_rendered = models.TextField(
        null=True, blank=True
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
        return reverse("game_catalog:system-detail", kwargs={"system": self.id})

    class Meta:
        ordering = ["name", "-publication_date"]


class PublishedGame(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDModel, models.Model
):
    """
    A published game.
    """

    title = models.CharField(
        max_length=150, db_index=True, help_text=_("Title of the game")
    )
    image = models.ImageField(null=True, blank=True)
    description = models.TextField(
        null=True, blank=True, help_text=_("Description of the game.")
    )
    description_rendered = models.TextField(null=True, blank=True)
    url = models.URLField(
        null=True, blank=True, help_text=_("More info can be found here.")
    )
    publication_date = models.DateField(
        null=True, blank=True, help_text=_("Release/publication date of game.")
    )

    def __str__(self):
        return self.title  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:game-detail", kwargs={"game": self.id})

    class Meta:
        ordering = ["title", "-publication_date"]


class GameEdition(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDWithSlugModel, models.Model
):
    """
    Record of editons as a child object of PublishedGame.
    """

    name = models.CharField(max_length=100, help_text=_('Edition label, e.g. "5E"'))
    game = models.ForeignKey(
        PublishedGame,
        on_delete=models.CASCADE,
        help_text=_("Which game is this an edition of?"),
        related_name="editions",
    )
    game_system = models.ForeignKey(
        GameSystem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("Which game system does this edition use?"),
        related_name="game_editions",
    )
    publisher = models.ForeignKey(
        GamePublisher,
        on_delete=models.CASCADE,
        help_text=_("Who published this edition?"),
    )
    image = models.ImageField(null=True, blank=True)
    description = models.TextField(
        null=True, blank=True, help_text=_("Description of the edition if applicable.")
    )
    description_rendered = models.TextField(null=True, blank=True)
    url = models.URLField(
        null=True,
        blank=True,
        help_text=_("More info can be found at this external site."),
    )
    release_date = models.DateField(
        null=True, blank=True, help_text=_("When was this released?")
    )

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "{} ({})".format(self.game.title, self.name)

    def get_absolute_url(self):
        return reverse("game_catalog:edition_detail", kwargs={"edition": self.slug})

    def get_image_object(self):
        if not self.image:
            sbooks = SourceBook.objects.filter(edition=self, corebook=True).order_by(
                "release_date", "created"
            )
            if sbooks.count() > 0 and sbooks[0].image:
                return sbooks[0].image
            else:
                return None
        return self.image

    class Meta:
        order_with_respect_to = "game"


class SourceBook(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDWithSlugModel, models.Model
):
    """
    Source book (as opposed to a module/adventure) published for a given edition.
    """

    title = models.CharField(max_length=255, help_text=_("Title of sourcebook."))
    edition = models.ForeignKey(
        GameEdition,
        on_delete=models.CASCADE,
        help_text=_("Edition this relates to."),
        related_name="sourcebooks",
    )
    image = models.ImageField(
        null=True, blank=True, help_text=_("Image of book cover, if available.")
    )
    corebook = models.BooleanField(
        default=False,
        help_text=_("Is this volume considered a corebook for the edition?"),
    )
    release_date = models.DateField(
        null=True, blank=True, help_text=_("When was this book published?")
    )
    isbn = ISBNField(
        null=True, blank=True, help_text=_("ISBN for this book, if available.")
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("game_catalog:sourcebook_detail", kwargs={"book": self.slug})

    class Meta:
        order_with_respect_to = "edition"


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
    parent_game_edition = models.ForeignKey(
        GameEdition,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Edition that this module uses for play."),
    )
    image = models.ImageField(null=True, blank=True)
    url = models.URLField(
        blank=True, null=True, help_text=_("More info can be found here.")
    )

    def __str__(self):
        return "{0} ({1})".format(
            self.title, self.parent_game_edition
        )  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:module-detail", kwargs={"module": self.id})

    class Meta:
        ordering = ["title", "-publication_date"]
