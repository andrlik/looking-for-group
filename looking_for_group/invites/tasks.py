from datetime import timedelta

from django.utils import timezone

from . import models


def clean_old_expired_invites():
    """
    Check for invites with status expired that expired over 30 days ago.
    Delete any records found.

    :returns: int - number of deleted invites.
    """
    old_invites = models.Invite.objects.filter(status='expired', expires_at__lte=timezone.now() - timedelta(days=30))
    deleted_rows, delete_dict = old_invites.delete()
    return deleted_rows
