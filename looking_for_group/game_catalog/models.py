import logging
from uuid import uuid4
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.urls import reverse
from isbn_field import ISBNField
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TaggedItemBase

# Create your models here.
logger = logging.getLogger('catalog')


class UUIDTaggedItem(GenericUUIDTaggedItemBase, TaggedItemBase):
    """
    UUID compatible tagged item management model.
    """

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class AbstractTaggedLinkedModel(models.Model):
    """
    Helper functions for collecting tags from linked objects.
    """

    tags = TaggableManager(through=UUIDTaggedItem)

    @classmethod
    def get_all_parent_objects(cls):
        """
        Fetch all releated objects to this for tag examination.
        """
        return [
            f for f in cls._meta.get_fields()
            if f.many_to_one and not f.auto_created and f.related_model
        ]

    @cached_property
    def inherited_tags(self):
        """
        Fetches tags for itself and all other linked model instances.
        """
        related_objects = self.get_all_parent_objects()
        logger.debug("Found {} related objects.".format(len(related_objects)))
        parent_tags = None
        for field in related_objects:
            obj = getattr(self, field.name)
            logger.debug("Parsing instance of class {}".format(obj.__class__))
            for prop in ["tags", "inherited_tags"]:
                if hasattr(obj, prop):
                    logger.debug("Found property: {}".format(prop))
                    tags_qs = getattr(obj, prop)
                    if tags_qs:
                        logger.debug("Tags found")
                        if not parent_tags:
                            logger.debug('First tag queryset')
                            parent_tags = tags_qs.all()
                        else:
                            logger.debug('Merging tags into existing queryset')
                            parent_tags = parent_tags.union(tags_qs.all())
        return parent_tags

    class Meta:
        abstract = True


class GamePublisher(TimeStampedModel, models.Model):
    """
    A publisher of games.
    """

    id = models.UUIDField(default=uuid4, primary_key=True)
    name = models.CharField(max_length=255, db_index=True, help_text=_("Company Name"))
    logo = models.ImageField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, help_text=_("Company URL"))

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("catalog:pub_detail", kwargs={"publisher", self.id})


class GameSystem(TimeStampedModel, AbstractTaggedLinkedModel, models.Model):
    """
    A root rule system potentially used for multiple games.
    """

    id = models.UUIDField(default=uuid4, primary_key=True)
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
    ogl_license = models.BooleanField(
        default=False,
        help_text=_("Released under an Open Gaming License?")
    )
    system_url = models.URLField(
        null=True, blank=True, help_text=_("More info can be found here.")
    )

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("catalog:sys_detail", kwargs={"system": self.id})


class PublishedGame(TimeStampedModel, AbstractTaggedLinkedModel, models.Model):
    """
    A published game.
    """

    id = models.UUIDField(default=uuid4, primary_key=True)
    title = models.CharField(
        max_length=150, db_index=True, help_text=_("Title of the game")
    )
    publisher = models.ForeignKey(
        GamePublisher, help_text=_("Publisher of the game."), on_delete=models.CASCADE
    )
    game_system = models.ForeignKey(
        GameSystem,
        null=True,
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

    def __str__(self):
        return self.name  # pragma: no cover

    def get_absolute_url(self):
        return reverse("catalog:game_detail", kwargs={"game": self.id})


class PublishedModule(TimeStampedModel, AbstractTaggedLinkedModel, models.Model):
    """
    A published campaign/adventure module that might be used as the basis for gameplay.
    """

    id = models.UUIDField(default=uuid4, primary_key=True)
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
        return "{0} ({1})".format(self.title, self.parent_game.title)  # pragma: no cover

    def get_absolute_url(self):
        return reverse("catalog:mod_detail", kwargs={"module": self.id})
