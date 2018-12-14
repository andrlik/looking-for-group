from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from notifications.signals import notify

from . import models
from ..users.models import User


@receiver(post_save, sender=models.MessageReport)
def notify_admin_on_new_report(sender, instance, created, *args, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True, is_superuser=True)
        total_pending = models.MessageReport.objects.filter(status='pending').count()
        for admin in admins:
            notify.send(instance.reporter, recipient=admin, verb="filed a new {} report. You now have {} pending reports to review.".format(instance.report_type, total_pending), target=instance)


@receiver(pre_save, sender=models.MessageReport)
def notify_reporter_on_status_change(sender, instance, *args, **kwargs):
    if instance.status != "pending":
        # fetch the current version as another object
        old_version = models.MessageReport.objects.get(pk=instance.pk)
        if old_version.status != instance.status:
            notify.send(instance, recipient=instance.reporter, verb="The status of your report has transitioned to {}".format(instance.get_status_display()))
