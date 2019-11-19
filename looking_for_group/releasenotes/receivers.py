import logging

from allauth.account.signals import user_logged_in
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from markdown import markdown

from ..users.models import User
from .models import ReleaseNote, ReleaseNotice
from .serializers import ReleaseNoteSerializer
from .signals import user_specific_notes_displayed

logger = logging.getLogger("releasenotes")


@receiver(post_save, sender=User)
def add_placeholder_version_shown(sender, instance, created, *args, **kwargs):
    """
    If this is a brand new user, show the latest version that they have seen.
    """
    if created:
        try:
            latest_note = ReleaseNote.objects.latest("release_date")
        except ObjectDoesNotExist:
            latest_note = None
        ReleaseNotice.objects.create(user=instance, latest_version_shown=latest_note)


@receiver(pre_save, sender=ReleaseNote)
def render_markdown_to_field(sender, instance, *args, **kwargs):
    """
    Render the markdown note as HTML into the rendered_field to have a db cache of the result.
    """
    if instance.notes:
        instance.notes_rendered = markdown(instance.notes)


@receiver(user_logged_in)
def check_for_release_notes_to_show(sender, request, user, *args, **kwargs):
    """
    Check to see what the last set of release notes was to show this user.
    """
    logger.debug(
        "User {} logged in. Checking which was the last release note they saw...".format(
            user.username
        )
    )
    latest_release_note = ReleaseNote.objects.latest("release_date")
    if not user.releasenotice.latest_version_shown:
        # This is a user that's never seen any release note. Simply set it to the current version.
        logger.debug(
            "This is a user that's never seen release notes. Setting to {}".format(
                latest_release_note.version
            )
        )
        user.releasenotice.latest_version_shown = latest_release_note
        user.releasenotice.save()
    elif (
        latest_release_note.release_date
        >= user.releasenotice.latest_version_shown.release_date
        and latest_release_note.version
        != user.releasenotice.latest_version_shown.version
    ):
        # We need to show them the release notes.
        logger.debug(
            "User last saw notes on version {}. Adding notes to session up to current release of {}".format(
                user.releasenotice.latest_version_shown.version,
                latest_release_note.version,
            )
        )
        notes_to_display = (
            ReleaseNote.objects.filter(
                release_date__gte=user.releasenotice.latest_version_shown.release_date
            )
            .exclude(version=user.releasenotice.latest_version_shown.version)
            .order_by("-release_date")
        )
        request.session["release_notes"] = ReleaseNoteSerializer(
            notes_to_display, many=True
        ).data
        logger.debug(
            "Updated session and set release notes to {}".format(
                request.session["release_notes"]
            )
        )
    else:
        logger.debug(
            "User {} has already seen latest version {}".format(
                user.username, latest_release_note.version
            )
        )


@receiver(user_specific_notes_displayed)
def update_latest_release_note_scene(sender, user, note_list, request, *args, **kwargs):
    """
    Update the latest note seen.
    """
    if note_list:
        logger.debug(
            "Received signal to update latest note seen for user {}, based on set {}".format(
                user.username, note_list
            )
        )
        latest_note = ReleaseNote.objects.get(version=note_list[0]["version"])
        user.releasenotice.latest_version_shown = latest_note
        user.releasenotice.save()
        logger.debug(
            "Update user {} with lastest version seen of {}".format(
                user.username, latest_note.version
            )
        )
        # This check is just to support the django test client
        if "release_notes" in request.session.keys():
            del request.session["release_notes"]
        logger.debug("Removed extraneous release notes from session.")
