from django.db.models.signals import post_save
from django.dispatch import receiver

from ..users.models import User
from .models import ReleaseNotice
from .utils import get_latest_rn_version


@receiver(post_save, sender=User)
def add_placeholder_version_shown(sender, instance, created, *args, **kwargs):
    """
    If this is a brand new user, show the latest version that they have seen.
    """
    if created:
        ReleaseNotice.objects.create(
            user=instance, latest_version_seen=get_latest_rn_version()
        )
