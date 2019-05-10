from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from ..game_catalog.utils import AbstractUUIDModel, AbstractUUIDWithSlugModel

# Create your models here.


class Tour(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    The top level of a given tour.
    """
    name = models.CharField(max_length=50, db_index=True, unique=True)
    description = models.TextField()
    users_completed = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="completed_tours", blank=True)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Step(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    The step in the given tour.
    """
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="steps")
    step_order = models.PositiveIntegerField(default=0, help_text=_("The order of this step. Note that the number must be unique for the tour."))
    target_id = models.CharField(max_length=100, help_text=_("The id of the html element target for this step."))
    step_title = models.CharField(max_length=50, help_text=_("The title that should appear for this step."))
    guide_text = models.TextField(help_text=_("The Markdown version of the explanation that you want to appear in the guide box for this step of the tour."))

    class Meta:
        ordering = ['tour', 'step_order']
        unique_together = ['tour', 'step_order']
