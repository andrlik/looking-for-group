from django.db import models
from django.template.defaultfilters import random
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

# Create your models here.


class MOTDManager(models.Manager):
    def get_motd(self):
        now = timezone.now()
        candidates = self.get_queryset().filter(enabled=True, timebased=True, start__lte=now, end__gte=now)
        if candidates.count() == 0:
            return self.get_random()
        return candidates

    def get_random(self):
        random_options = self.get_queryset().filter(timebased=False, enabled=True)
        if random_options.count() == 0:
            return None
        random_selection = random(list(random_options))
        return [random_selection]



class MOTD(TimeStampedModel, models.Model):
    """
    Represents either a time based motd the day or a random selection of other options.
    """
    enabled = models.BooleanField(default=True, help_text=_("Should this be included in the potential results for a message of the day?"))
    timebased = models.BooleanField(default=False, help_text=_("Is this message based on a date range or should it always be an option?"))
    start = models.DateTimeField(null=True, blank=True, help_text=_("The earliest time this message should begin appearing."))
    end = models.DateTimeField(null=True, blank=True, help_text=_("The latest time this message should appear."))
    message = models.TextField(max_length=500, help_text=_("The plain text of the message you want to appear."))
    monospace = models.BooleanField(default=False, help_text=_("Display this message using a monospace typeface."))

    objects = MOTDManager()

    def __str__(self):
        return self.message

    class Meta:
        ordering = ['-end', '-start']
        verbose_name = "MOTD"
        verbose_name_plural = "MOTDs"
