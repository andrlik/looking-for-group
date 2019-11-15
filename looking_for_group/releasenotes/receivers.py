from allauth.account.signals import user_logged_in
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from markdown import markdown

from ..users.models import User
from .models import ReleaseNote, ReleaseNotice


@receiver(post_save, sender=User)
def add_placeholder_version_shown(sender, instance, created, *args, **kwargs):
    """
    If this is a brand new user, show the latest version that they have seen.
    """
    if created:
        try:
            latest_note = ReleaseNote.objects.lastest("date_released")
        except ObjectDoesNotExist:
            latest_note = None
        ReleaseNotice.objects.create(user=instance, latest_version_seen=latest_note)


@receiver(pre_save, sender=ReleaseNote)
def render_markdown_to_field(sender, instance, *args, **kwargs):
    """
    Render the markdown note as HTML into the rendered_field to have a db cache of the result.
    """
    if instance.notes:
        instance.notes_rendered = markdown(instance.notes)


@receiver(user_logged_in)
def check_for_release_notes_to_show(sender, instance, request, user, *args, **kwargs):
    """
    Check to see what the last set of release notes was to show this user.
    """
    latest_release_note = ReleaseNote.objects.latest("release_date")
    if not user.releasenotice.latest_version_shown:
        # This is a user that's never seen any release note. Simply set it to the current version.
        user.releasenotice.latest_version_shown = latest_release_note
        user.releasenotice.save()
    elif latest_release_note.version < user.releasenotice.latest_version_seen.version:
        # We need to show them the release notes.
        notes_to_display = ReleaseNote.objects.filter(
            version__gt=user.releasenotice.latest_version_shown.version
        ).order_by("-version")
        request.session["release_notes"] = notes_to_display
