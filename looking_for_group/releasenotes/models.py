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
    latest_version_shown = VersionField(
        null=True, blank=True, help_text=_("Latest version of release notes shown.")
    )

    def __str__(self):
        return _(
            "{} saw notes for version {} at {}".format(
                self.user, self.latest_version_shown, self.created
            )
        )
