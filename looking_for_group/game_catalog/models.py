import logging

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from isbn_field import ISBNField
from model_utils.models import TimeStampedModel

from .utils import AbstractTaggedLinkedModel, AbstractUUIDModel, AbstractUUIDWithSlugModel

# Create your models here.
logger = logging.getLogger("catalog")


SUGGESTION_STATUS_CHOICES = (
    ("new", _("New")),
    ("approved", _("Approved")),
    ("rejected", _("Rejected")),
)


class GamePublisher(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A publisher of games.
    """

    name = models.CharField(max_length=255, db_index=True, help_text=_("Company Name"))
    logo = models.ImageField(
        null=True, blank=True, upload_to="catalog/publisher_logos/%Y/%m/%d"
    )
    url = models.URLField(null=True, blank=True, help_text=_("Company URL"))
    description = models.TextField(
        null=True, blank=True, help_text=_("Description of the publisher.")
    )
    suggested_corrections = GenericRelation("game_catalog.SuggestedCorrection")

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:pub-detail", kwargs={"publisher": self.id})

    class Meta:
        ordering = ["name"]
        verbose_name = _("Publisher")


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
    description_rendered = models.TextField(null=True, blank=True)
    original_publisher = models.ForeignKey(
        GamePublisher,
        help_text=_("Publisher who originally released the rules system."),
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        null=True, blank=True, upload_to="catalog/game_system_covers/%Y/%m/%d"
    )
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
    collected_copies = GenericRelation("rpgcollections.Book")
    suggested_corrections = GenericRelation("game_catalog.SuggestedCorrection")

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:system-detail", kwargs={"system": self.id})

    class Meta:
        ordering = ["name", "-publication_date"]
        verbose_name = _("Game System")


class PublishedGame(
    TimeStampedModel, AbstractTaggedLinkedModel, AbstractUUIDModel, models.Model
):
    """
    A published game.
    """

    title = models.CharField(
        max_length=150, db_index=True, help_text=_("Title of the game")
    )
    image = models.ImageField(
        null=True, blank=True, upload_to="catalog/base_game_covers/%Y/%m/%d"
    )
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
    suggested_corrections = GenericRelation("game_catalog.SuggestedCorrection")

    def __str__(self):
        return self.title  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:game-detail", kwargs={"game": self.id})

    class Meta:
        ordering = ["title", "-publication_date"]
        verbose_name = _("Published Game")


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
    image = models.ImageField(
        null=True, blank=True, upload_to="catalog/game_edition_covers/%Y/%m/%d"
    )
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
    suggested_corrections = GenericRelation("game_catalog.SuggestedCorrection")

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
        verbose_name = _("Game Edition")


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
        null=True,
        blank=True,
        upload_to="catalog/sourcebook_covers/%Y/%m/%d",
        help_text=_("Image of book cover, if available."),
    )
    corebook = models.BooleanField(
        default=False,
        help_text=_("Is this volume considered a corebook for the edition?"),
    )
    publisher = models.ForeignKey(
        GamePublisher,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text=_("Publisher of this sourcebook."),
    )
    release_date = models.DateField(
        null=True, blank=True, help_text=_("When was this book published?")
    )
    isbn = ISBNField(
        null=True, blank=True, help_text=_("ISBN for this book, if available.")
    )
    collected_copies = GenericRelation("rpgcollections.Book")
    suggested_corrections = GenericRelation("game_catalog.SuggestedCorrection")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.publisher and self.edition:
            self.publisher = self.edition.publisher
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("game_catalog:sourcebook_detail", kwargs={"book": self.slug})

    class Meta:
        order_with_respect_to = "edition"
        verbose_name = _("Source Book")


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
    image = models.ImageField(
        null=True, blank=True, upload_to="catalog/module_covers/%Y/%m/%d"
    )
    url = models.URLField(
        blank=True, null=True, help_text=_("More info can be found here.")
    )
    collected_copies = GenericRelation("rpgcollections.Book")
    suggested_corrections = GenericRelation("game_catalog.SuggestedCorrection")

    def __str__(self):
        return self.title  # pragma: no cover

    def get_absolute_url(self):
        return reverse("game_catalog:module-detail", kwargs={"module": self.id})

    class Meta:
        ordering = ["title", "-publication_date"]
        verbose_name = _("Module/Adventure")


class SuggestedCorrection(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    A suggested change to an existing listing.
    """

    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.CharField(
        max_length=30, choices=SUGGESTION_STATUS_CHOICES, default="new", db_index=True
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=90, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    new_title = models.CharField(
        verbose_name=_("New Name/Title"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Suggested title/name change, if any."),
    )
    new_isbn = ISBNField(
        null=True, blank=True, help_text=_("ISBN of item, if applicable")
    )
    new_release_date = models.DateField(
        null=True, blank=True, help_text=_("Suggested change to the release date.")
    )
    new_url = models.DateField(null=True, blank=True, help_text=_("New suggested url"))
    new_image = models.ImageField(
        null=True, blank=True, upload_to="catalog/corrections/%Y/%m/%d"
    )
    new_description = models.TextField(
        null=True, blank=True, help_text=_("New description, if applicable to object.")
    )
    new_tags = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Suggested tags for the item"),
    )
    other_notes = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "Any other details or suggestions we should incorporate into the correction."
        ),
    )

    @property
    def title(self):
        if hasattr(self.content_object, "title"):
            return self.content_object.title
        return self.content_type.name

    def delete(self, *args, **kwargs):
        if self.new_image:
            self.new_image.delete(save=True)
        return super().delete(*args, **kwargs)

    def transfer_image(self):
        """
        Transfer image file to new location and then delete from this record.
        """
        pass

    def get_absolute_url(self):
        return reverse("game_catalogs:correction_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return "Suggested Correction for {}: {}".format(self.content_type, self.title)

    class Meta:
        ordering = ["-created", "status"]
        verbose_name = _("Suggested Correction")


class SuggestedAddition(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    A suggested new entry to the catalog.
    """

    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.CharField(
        max_length=30, choices=SUGGESTION_STATUS_CHOICES, default="new", db_index=True
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    title = models.CharField(
        verbose_name=_("Name/Title"),
        max_length=255,
        help_text=_("Name or title of suggested addition."),
    )
    description = models.TextField(
        null=True, blank=True, help_text=_("Description for the addition.")
    )
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="catalog/suggested_additions/%Y/%m/%d",
        help_text=_("Cover image or logo"),
    )
    url = models.URLField(null=True, blank=True, help_text=_("Suggested url field"))
    ogl_license = models.BooleanField(
        help_text=_("Is this released under an OGL license?")
    )
    publisher = models.ForeignKey(
        GamePublisher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("Publisher of item."),
    )
    game = models.ForeignKey(
        PublishedGame,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("For what game?"),
    )
    edition = models.ForeignKey(
        GameEdition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("For which edition?"),
    )
    release_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Release date for addition. When was this published?"),
    )
    isbn = ISBNField(null=True, blank=True, help_text=_("ISBN for item, if applicable"))
    suggested_tags = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Comma seperated list of suggested tags"),
    )

    def __str__(self):
        return "Suggested {}: {}".format(self.content_type, self.title)

    def get_absolute_url(self):
        return reverse("game_catalog:addition", kwargs={"slug": self.slug})

    def transfer_image(self):
        pass

    class Meta:
        ordering = ["-created", "status"]
        verbose_name = _("Suggested Addition")
