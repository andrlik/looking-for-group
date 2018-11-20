from django.db import models
from model_utils.models import TimeStampedModel
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from datetime import timedelta

from ...game_catalog.utils import AbstractUUIDWithSlugModel
from ...gamer_profiles.models import GamerProfile

# Create your models here.


INVITE_STATUS_CHOICES = (
    ("pending", _("Pending")),
    ("accepted", _("Accepted")),
    ("expired", _("Expired"))
)


class Invite(TimeStampedModel, AbstractUUIDWithSlugModel, models.Model):
    """
    Invites with generic foreign key to another item.
    """
    label = models.CharField(max_length=50, help_text=_("Label for the invite for your reference."))
    created_by = models.ForeignKey(GamerProfile, on_delete=models.CASCADE, help_text=_("Invite is created by this gamer."))
    expires_at = models.DateTimeField(blank=True, help_text=_("Expiration date for this invite."), db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, help_text=_("Content type of the related object."))
    object_id = models.CharField(max_length=50, help_text=_("Object id of linked object."), db_index=True)
    content_object = GenericForeignKey(content_type, object_id)
    status = models.CharField(max_length=25, choices=INVITE_STATUS_CHOICES, default="pending", db_index=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiration = timezone.now() + timedelta(days=30)
            if self.created:
                expiration = self.created + timedelta(days=30)
            self.expires_at = expiration
        if self.expires_at < timezone.now():
            self.status = "expired"
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created']
