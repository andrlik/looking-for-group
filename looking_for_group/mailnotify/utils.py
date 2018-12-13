from anymail.message import AnymailMessage
from django.utils.translation import ugettext_lazy as _
from django_q.tasks import async_task
from markdown import markdown
from notifications.signals import notify
from postman.utils import format_body, format_subject


def send(users, label, extra_context):
    """
    An intercept for the standard django-postman notify script that allows us to tweak it.
    """
    verb = _("sent you a message:")
    msg = extra_context['pm_message']
    if label == "postman_rejection":
        verb = _("your message to {} was not delivered due to our filtering rules.".format(msg.recipient))
    if label == "postman_reply":
        verb = _("sent a reply to your message:")
    for user in users:
        notify.send(msg.sender, recipient=user, verb=verb, target=msg)
        if user.gamerprofile.preferences.email_messages:
            async_task(send_email_notification, user, msg)


def send_email_notification(user, msg):
    email_msg = AnymailMessage(to=user.email, subject=format_subject(msg.subject), body=format_body(msg.sender, msg.body))
    email_msg.attach_alternative("<html>{}</html>".format(markdown(format_body(msg.sender, msg.body))), "text/html")
    email_msg.send()
