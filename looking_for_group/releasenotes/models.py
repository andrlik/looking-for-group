from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from semantic_version.django_fields import VersionField

from ..game_catalog.utils import AbstractUUIDModel

# Create your models here.


class ReleaseNotice(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Represents the latest release notice that a given user has seen.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    latest_version_shown = models.ForeignKey(
        "ReleaseNote", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        str_response = "{} saw notes for version {} at {}"
        str_args = None
        if self.latest_version_shown:
            str_args = [
                self.user.username,
                self.latest_version_shown.version,
                self.modified,
            ]
        else:
            str_args = [self.user.username, None, self.created]
        return str_response.format(*str_args)


class ReleaseNote(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Represents parsed release note entries. We store the results in the DB rather than parsing the changelog everytime, which could be prone to errors.
    """

    version = VersionField(unique=True, help_text=_("Semantic version for the update."))
    release_date = models.DateField(
        db_index=True, help_text=_("Official release date for this version.")
    )
    notes = models.TextField(
        help_text=_("The notes for the release. This should be stored in Markdown.")
    )
    notes_rendered = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "HTML rendered version of the notes field. Precalculated at creation to reduce template processing."
        ),
    )

    def __str__(self):
        return str(self.version)

    class Meta:
        ordering = ["-release_date"]
