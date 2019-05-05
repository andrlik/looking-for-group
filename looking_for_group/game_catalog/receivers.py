import logging

from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from markdown import markdown
from notifications.signals import notify

from . import models

logger = logging.getLogger("catalog")


@receiver(pre_save, sender=models.PublishedGame)
@receiver(pre_save, sender=models.GameEdition)
@receiver(pre_save, sender=models.GameSystem)
def render_markdown_body(sender, instance, *args, **kwargs):
    if instance.description:
        instance.description_rendered = markdown(instance.description)
    else:
        instance.description_rendered = None


@receiver(pre_save, sender=models.SuggestedCorrection)
def check_for_correction_stat_increments(sender, instance, *args, **kwargs):
    """
    Check to see if we should increment the profile stats based on
    acceptance/rejection.
    """
    try:
        logger.debug("Checking to see if there is an older version of this object.")
        old_version = models.SuggestedCorrection.objects.get(id=instance.pk)
        logger.debug("Checking previous status of object.")
        if old_version.status != instance.status:
            logger.debug("Statuses do not match. Evaluating...")
            if old_version.status == "new":
                logger.debug("Status has changed from [new]...")
                if instance.status == "approved":
                    logger.debug(
                        "Status has changed from new to approved. Incrementing approved count."
                    )
                    instance.submitter.gamerprofile.submitted_corrections_approved = (
                        F("submitted_corrections_approved") + 1
                    )

                else:
                    logger.debug(
                        "Status has changed from new to rejected. Incrementing rejected count."
                    )
                    instance.submitter.gamerprofile.submitted_corrections_rejected = (
                        F("submitted_corrections_rejected") + 1
                    )
            elif old_version.status == "approved":
                logger.debug(
                    "Old status was [approved]. Decrementing approved count and evaluating..."
                )
                instance.submitter.gamerprofile.submitted_corrections_approved = (
                    F("submitted_corrections_approved") - 1
                )
                if instance.status == "rejected":
                    logger.debug(
                        "status changed from approved to rejected. Incrementing rejected count."
                    )
                    instance.submitter.gamerprofile.submitted_corrections_rejected = (
                        F("submitted_corrections_rejected") + 1
                    )
            else:
                logger.debug(
                    "Status was [rejected]. Decrementing rejected count and evaluating..."
                )
                instance.submitter.gamerprofile.submitted_corrections_rejected = (
                    F("submitted_corrections_rejected") - 1
                )
                if instance.status == "approved":
                    logger.debug(
                        "Status was changed from rejected to approved. Incrementing approval count."
                    )
                    instance.submitter.gamerprofile.submitted_corrections_approved = (
                        F("submitted_corrections_approved") + 1
                    )
            logger.debug("Count changes complete. Saving gamer profile.")
            instance.submitter.gamerprofile.save()
            logger.debug("Refreshing gamerprofile from db...")
            instance.submitter.gamerprofile.refresh_from_db()
            logger.debug(
                "New counts are CORRECTIONS [{}], APPROVALS [{}], REJECTIONS [{}]".format(
                    instance.submitter.gamerprofile.submitted_corrections,
                    instance.submitter.gamerprofile.submitted_corrections_approved,
                    instance.submitter.gamerprofile.submitted_corrections_rejected,
                )
            )
            if instance.status == "approved":
                logger.debug(
                    "Since instance was approved, sending notification to submitter."
                )
                notify.send(
                    instance.reviewer,
                    recipient=instance.submitter,
                    verb=_(
                        "has approved your suggested correction for {}".format(
                            instance.title
                        )
                    ),
                )
            if instance.status == "rejected":
                logger.debug(
                    "Since instance was rejected, sending notification to submitter."
                )
                notify.send(
                    instance.reviewer,
                    recipient=instance.submitter,
                    verb=_(
                        "rejected your suggested correction for {}".format(
                            instance.title
                        )
                    ),
                )
        else:
            logger.debug("Statuses are the same. Ignoring.")
    except ObjectDoesNotExist:
        logger.debug("No previous version of object to compare with...")
        pass  # This is a new correction. We'll let the post_save handler deal with it.


@receiver(post_save, sender=models.SuggestedCorrection)
def check_to_increment_correction_stats(sender, instance, created, *args, **kwargs):
    """
    If created, increment the submitted count and then notify the rpgeditors.
    """
    if created:
        logger.debug(
            "This is a new correction object. Incrementing submission count..."
        )
        instance.submitter.gamerprofile.submitted_corrections = (
            F("submitted_corrections") + 1
        )
        instance.submitter.gamerprofile.save()
        instance.submitter.gamerprofile.refresh_from_db()
        logger.debug(
            "Total submissions is now equal to {}".format(
                instance.submitter.gamerprofile.submitted_corrections
            )
        )
        try:
            logger.debug("Checking to see if editors exist...")
            editorgroup = Group.objects.get(name="rpgeditors")
            for user in editorgroup.user_set.all():
                logger.debug("sending editor notification to user {}".format(user))
                notify.send(
                    instance.submitter,
                    recipient=user,
                    verb=_("submitted a new correction for review."),
                    target=instance,
                )
        except ObjectDoesNotExist:
            pass  # No one to notify


@receiver(pre_save, sender=models.SuggestedAddition)
def check_for_addition_stat_increments(sender, instance, *args, **kwargs):
    """
    Check to see if we should increment the profile stats based on
    acceptance/rejection.
    """
    try:
        old_version = models.SuggestedAddition.objects.get(id=instance.pk)
        if old_version.status != instance.status:
            if old_version.status == "new":
                if instance.status == "approved":
                    instance.submitter.gamerprofile.submitted_additions_approved = (
                        F("submitted_additions_approved") + 1
                    )

                else:
                    instance.submitter.gamerprofile.submitted_additions_rejected = (
                        F("submitted_additions_rejected") + 1
                    )
            elif old_version.status == "approved":
                instance.submitter.gamerprofile.submitted_additions_approved = (
                    F("submitted_additions_approved") - 1
                )
                if instance.status == "rejected":
                    instance.submitter.gamerprofile.submitted_additions_rejected = (
                        F("submitted_additions_rejected") + 1
                    )
            else:
                instance.submitter.gamerprofile.submitted_additions_rejected = (
                    F("submitted_additions_rejected") - 1
                )
                if instance.status == "approved":
                    instance.submitter.gamerprofile.submitted_additions_approved = (
                        F("submitted_additions_approved") + 1
                    )
            instance.submitter.gamerprofile.save()
            if instance.status == "approved":
                notify.send(
                    instance.reviewer,
                    recipient=instance.submitter,
                    verb=_(
                        "has approved your suggested addition of {}".format(
                            instance.title
                        )
                    ),
                )
            if instance.status == "rejected":
                notify.send(
                    instance.reviewer,
                    recipient=instance.submitter,
                    verb=_(
                        "rejected your suggested addition of {}".format(instance.title)
                    ),
                )
    except ObjectDoesNotExist:
        pass  # This is a new addition. We'll let the post_save handler deal with it.


@receiver(post_save, sender=models.SuggestedAddition)
def check_to_increment_addition_stats(sender, instance, created, *args, **kwargs):
    """
    If created, increment the submitted count and then notify the rpgeditors.
    """
    if created:
        instance.submitter.gamerprofile.submitted_additions = (
            F("submitted_additions") + 1
        )
        instance.submitter.gamerprofile.save()
        try:
            editorgroup = Group.objects.get(name="rpgeditors")
            for user in editorgroup.user_set.all():
                notify.send(
                    instance.submitter,
                    recipient=user,
                    verb=_("submitted a new addition for review."),
                    target=instance,
                )
        except ObjectDoesNotExist:
            pass  # No one to notify
