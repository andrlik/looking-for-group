from django.contrib.sites.models import Site
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from notifications.signals import notify

from . import models
from ..users.models import User
from .rules import is_not_silenced


@receiver(post_save, sender=models.MessageReport)
def notify_admin_on_new_report(sender, instance, created, *args, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True, is_superuser=True)
        total_pending = models.MessageReport.objects.filter(status='pending').count()
        for admin in admins:
            notify.send(instance.reporter, recipient=admin, verb=_("filed a new {} report. You now have {} pending reports to review.".format(instance.report_type, total_pending)), target=instance)


@receiver(pre_save, sender=models.MessageReport)
def notify_reporter_on_status_change(sender, instance, *args, **kwargs):
    if instance.status != "pending":
        # fetch the current version as another object
        old_version = models.MessageReport.objects.get(pk=instance.pk)
        if old_version.status != instance.status:
            notify.send(instance, recipient=instance.reporter, verb=_("The status of your report has transitioned to {}".format(instance.get_status_display())))


@receiver(post_delete, sender=models.SilencedUser)
def notify_if_no_longer_silenced(sender, instance, *args, **kwargs):
    if is_not_silenced(instance.user):
        site = Site.objects.all()[0]
        notify.send(site, recipient=instance.user, verb=_("Your silence has been lifted. Please message reponsibly."))
