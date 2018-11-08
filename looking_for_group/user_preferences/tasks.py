import logging

from django.core.mail import send_mail
from django.db import transaction
from django_q.tasks import async_task
from markdown import markdown
from notifications.models import Notification

from .models import Preferences

logger = logging.getLogger("games")


def form_email_body(user, notification_list):
    body_template = """
     Hi {},

     Here's your digest of unread notifications on LFG Directory.

     {}

    You have received this message because you have requested that we send you email digests of your unread notifications. You can turn this off at any time in settings.

    Thanks again for using our site! We love you.
     """
    text_list = []
    for notification in notification_list:
        target_text = ""
        if notification.target:
            target_text = "in relation to {}"
        text_list.append(
            "- {} {} {} {}".format(
                notification.actor,
                notification.verb,
                notification.action_object,
                target_text,
            )
        )
    user_string = user.username
    if user.display_name:
        user_string = user.display_name
    return body_template.format(user_string, "\n".join(text_list))


def send_digest_email(user, notifications):
    email_to_use = user.email
    if email_to_use:
        body = form_email_body(user, notifications)
        result = send_mail(
            subject="Unread notifications from LFG Directory",
            message=body,
            from_email="noreply@mg.lfg.directory",
            recipient_list=[email_to_use],
            html_message=markdown(body),
        )
        if result == 0:
            logger.error("An email to {} failed to send".format(email_to_use))
        else:
            logger.debug("An email to {} was successfully sent".format(email_to_use))
            with transaction.atomic():
                notifications.update(emailed=True)


def get_users_with_digests(pretend=False):
    user_targets = Preferences.objects.filter(notification_digests=True).select_related(
        "gamer", "gamer__user"
    )
    if pretend:
        print("Found {} user targets".format(user_targets))
        return
    return user_targets


def get_notifications_for_userlist(user_targets):
    if user_targets.count() > 0:
        for user in [pref.gamer.user for pref in user_targets]:
            unread = Notification.objects.filter(
                recipient=user, unread=True, emailed=False
            )
            if unread.count() > 0:
                async_task(send_digest_email, user, unread)


def perform_daily_digests():
    user_list = get_users_with_digests()
    get_notifications_for_userlist(user_list)
