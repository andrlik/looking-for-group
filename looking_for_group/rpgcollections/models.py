from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from model_utils.models import TimeStampedModel

from ..game_catalog.models import AbstractUUIDWithSlugModel


# Create your models here.
class GameLibrary(AbstractUUIDWithSlugModel):
    """
    Top level object for an individual user's library.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    num_titles = models.PositiveIntegerField(default=0)
    num_pdf = models.PositiveIntegerField(default=0)
    num_print = models.PositiveIntegerField(default=0)
    distinct_game_editions = models.PositiveIntegerField(default=0)
    distinct_sourcebooks = models.PositiveIntegerField(default=0)
    distinct_modules = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "{0}'s library".format(self.user.username)

    def get_absolute_url(self):
        return reverse('gamer_profiles:book-list', kwargs={"gamer": self.user.username})


class Book(TimeStampedModel, AbstractUUIDWithSlugModel):
    """
    A library entry for a user.
    """

    library = models.ForeignKey(GameLibrary, on_delete=models.CASCADE)
    in_print = models.BooleanField(default=False, help_text=_("Do you have a print copy of this book?"))
    in_pdf = models.BooleanField(default=False, help_text=_("Do you have a PDF/Ebook copy of this book?"))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(
        max_length=70, help_text=_("ID of the related object.")
    )
    content_object = GenericForeignKey("content_type", "object_id")

    @property
    def title(self):
        return self.get_title()

    def get_title(self):
        if self.content_object:
            if hasattr(self.content_object, 'title'):
                return self.content_object.title
            return self.content_object.name
        return None

    @property
    def cover(self):
        return self.get_cover()

    def get_cover(self):
        if hasattr(self.content_object, "image"):
            return self.content_object.image

    def __str__(self):
        typestr = ""
        if self.in_print and self.in_pdf:
            typestr = "Print | PDF"
        elif self.in_print and not self.in_pdf:
            typestr = "Print"
        elif not self.in_print and self.in_pdf:
            typestr = "PDF"
        else:
            typestr = "Unknown"
        return "{0} ({1})".format(self.title, typestr)

    def get_absolute_url(self):
        return reverse("rpgcollections:book-detail", kwargs={"book": self.slug})
