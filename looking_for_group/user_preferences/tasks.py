import logging

from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import transaction
from django.template import Context
from django.template.loader import render_to_string
from django_q.tasks import async_task
from markdown import markdown
from notifications.models import Notification

from .models import Preferences

logger = logging.getLogger("games")


def form_email_body(user, notification_list):
    plaintext_context = Context(autoescape=False)
    text_body = render_to_string("user_preferences/message_body.txt", {'user': user, 'notifications': notification_list}, plaintext_context)
    html_body = markdown(text_body)
    return text_body, html_body


def send_digest_email(user, notifications):
    email_to_use = user.email
    if email_to_use:
        body, html_body = form_email_body(user, notifications)
        msg = EmailMultiAlternatives(subject="LFG Directory Activity Digest", from_email="noreply@mg.lfg.directory", to=[email_to_use], body=body)
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
        with transaction.atomic():
            notifications.update(emailed=True)


def get_users_with_digests(pretend=False):
    user_targets = Preferences.objects.filter(notification_digest=True).select_related(
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
