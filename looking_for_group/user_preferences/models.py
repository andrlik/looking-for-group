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
    email_messages = models.BooleanField(verbose_name='Email messages', default=False, help_text=_("When a user sends me a message, send a copy of it to my email."))
    community_subscribe_default = models.BooleanField(verbose_name='Default for community subscriptions', default=False, help_text=_("When joining a community, receive notifications of new games being posted there by default. (You can also edit this for individual communities.)"))

    def __str__(self):
        return "Settings for {}".format(self.gamer)

    def get_absolute_url(self):
        return reverse_lazy('user_preferences:setting-view')
