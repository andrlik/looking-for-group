from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django_q.tasks import async_task

from . import models
from .signals import issue_state_changed
from .tasks import notify_subscribers_of_issue_state_change, notify_subscribers_of_new_comment, queue_issue_for_sync


@receiver(post_save, sender=models.IssueCommentLink)
def add_subscriber_to_issue_on_new_comment(sender, instance, created, *args, **kwargs):
    """
    When a new comment is created, add it to the creator to the subscriber list if not already subscribed.
    """
    if created and instance.creator:
        instance.master_issue.subscribers.add(instance.creator)


@receiver(post_save, sender=models.IssueCommentLink)
def subscriber_updates(sender, instance, created, *args, **kwargs):
    """
    When a new comment is added to an issue, notify all the subscribers.
    """
    if created:
        async_task(notify_subscribers_of_new_comment, instance)


@receiver(post_save, sender=models.IssueCommentLink)
def update_issue_on_new_comment(sender, instance, created, *args, **kwargs):
    if created and instance.master_issue.last_sync < instance.created:
        instance.master_issue.cached_comment_count = F("cached_comment_count") + 1
        instance.master_issue.save()
        async_task(queue_issue_for_sync, instance.master_issue)


@receiver(post_delete, sender=models.IssueCommentLink)
def update_issue_on_comment_delete(sender, instance, *args, **kwargs):
    async_task(queue_issue_for_sync, instance.master_issue)


@receiver(issue_state_changed)
def fire_state_change_notfication(
    sender, issue, user, old_status, new_status, *args, **kwargs
):
    async_task(
        notify_subscribers_of_issue_state_change, issue, user, old_status, new_status
    )
