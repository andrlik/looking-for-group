from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from ..game_catalog.utils import AbstractUUIDWithSlugModel

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
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_invites', help_text=_("Invite is created by this gamer."))
    expires_at = models.DateTimeField(blank=True, help_text=_("Expiration date for this invite."), db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, help_text=_("Content type of the related object."))
    object_id = models.CharField(max_length=50, help_text=_("Object id of linked object."), db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    status = models.CharField(max_length=25, choices=INVITE_STATUS_CHOICES, default="pending", db_index=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='accepted_invites', help_text=_("Who accepted this invite?"), null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiration = timezone.now() + timedelta(days=30)
            if self.created:
                expiration = self.created + timedelta(days=30)
            self.expires_at = expiration
        if self.expires_at < timezone.now() and self.status == "pending":
            self.status = "expired"
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created']
