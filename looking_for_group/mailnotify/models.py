from anymail.message import AnymailMessage
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django_q.tasks import async_task
from markdown import markdown
from model_utils.models import TimeStampedModel
from notifications.signals import notify
from postman.models import Message
from postman.utils import format_body, format_subject

from ..game_catalog.utils import AbstractUUIDModel, AbstractUUIDWithSlugModel
from ..users.models import User


def send(users, label, extra_context):
    """
    An intercept for the standard django-postman notify script that allows us to tweak it.
    """
    verb = _("sent you a message:")
    msg = extra_context["pm_message"]
    if label == "postman_rejection":
        verb = _(
            "your message to {} was not delivered due to our filtering rules.".format(
                msg.recipient
            )
        )
    if label == "postman_reply":
        verb = _("sent a reply to your message:")
    for user in users:
        notify.send(msg.sender, recipient=user, verb=verb, target=msg)
        if user.gamerprofile.preferences.email_messages == True:
            async_task(send_email_notification, user, msg)


def send_email_notification(user, msg):
    email_msg = AnymailMessage(
        to=user.email,
        subject=format_subject(msg.subject),
        body=format_body(msg.sender, msg.body),
    )
    email_msg.attach_alternative(
        "<html>{}</html>".format(markdown(format_body(msg.sender, msg.body))),
        "text/html",
    )
    email_msg.send()


class MessageReport(TimeStampedModel, AbstractUUIDWithSlugModel):
    """
    An object that can be used to report harrassment and/or spam.
    """

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("Who reported this message."),
        related_name="issues",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        help_text=_("The offending message."),
        related_name="related_complaints",
    )
    plaintiff = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("Who is this report about?"),
        related_name="complaints_received",
    )
    report_type = models.CharField(
        max_length=20,
        choices=[("spam", _("Spam")), ("harrassment", _("Harassment"))],
        help_text=_("Which type of complaint?"),
        db_index=True,
        default="spam",
    )
    details = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "Any addtional details you can provide to help us while we evaluate this complaint."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", _("Pending")),
            ("review", _("In review")),
            ("done", _("Completed")),
        ],
        default="pending",
    )
    admin_response = models.TextField(
        null=True, blank=True, help_text=_("Site administrator response.")
    )

    def __str__(self):
        return "{} report regarding {} filed by {}".format(
            self.get_report_type_display(), self.plaintiff, self.reporter
        )

    def get_absolute_url(self):
        return reverse_lazy("postman:report_detail", kwargs={"report": self.slug})

    def warn_plaintiff(self):
        site = Site.objects.all()[0]
        notify.send(
            site,
            recipient=self.plaintiff,
            verb=_(
                "We have received {} complaints regarding your messages. These have been evaluated by our staff and found to be be valid complaints. Further complaints could result in you being silenced or suspended from the site.".format(
                    self.report_type
                )
            ),
        )

    def silence_plaintiff(self, end_date=None):
        SilencedUser.objects.create(
            user=self.offender, releated_report=self, ending=end_date
        )
        site = Site.objects.all()[0]
        notify.send(
            site,
            recipient=self.plaintiff,
            verb=_(
                "Due to numerous valid complaints your account has been silenced until {}. You will not be able to send other users messages during that time.".format(
                    end_date or "eternity"
                )
            ),
        )


class SilencedUser(TimeStampedModel, AbstractUUIDModel):
    """
    Silencing a user prevents them from sending messages to anyone.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text=_("User silenced."),
        related_name="silence_terms",
    )
    related_report = models.ForeignKey(
        MessageReport,
        on_delete=models.CASCADE,
        help_text=_("The report that initiaited this silence."),
    )
    ending = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "When does the silencing period end? Leave blank for eternal silence."
        ),
    )

    def __str__(self):
        return "{} silended until {}".format(self.user, self.ending or "eternity")

    def get_absolute_url(self):
        return reverse_lazy("postman:silence_detail", kwargs={"silence": self.pk})
