from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from ..game_catalog.utils import AbstractUUIDModel
from ..gamer_profiles.models import GamerProfile

# Create your models here.


class Preferences(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    An object for storing notification preferences.
    """
    gamer = models.OneToOneField(GamerProfile, on_delete=models.CASCADE)
    news_emails = models.BooleanField(default=False, help_text=_("Send me occasionally news about the site. NOTE: We will still send you essential notices such as privacy policy and terms of service information, etc."))
    notification_digest = models.BooleanField(default=False, help_text=_("Send me email digests of unread notifications."))
    feedback_volunteer = models.BooleanField(default=False, help_text=_('Is it ok if we occasionally reach out to directly to solicit site feedback?'))

    def __str__(self):
        return "Settings for {}".format(self.gamer)

    def get_absolute_url(self):
        return reverse_lazy('user_preferences:setting-view')
