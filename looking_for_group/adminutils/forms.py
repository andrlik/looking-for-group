from django import forms
from django.utils.translation import ugettext_lazy as _

NOTIFICATION_FILTER_CHOICES = (
    ("news_emails", _("News Emails")),
    ("notification_digest", _("Notification Digests")),
    ("feedback_volunteer", _("Feedback Volunteer")),
)


class NotificationForm(forms.Form):
    """
    An unbound form used to create a new notification to be sent to a mass group.
    """

    message = forms.CharField(
        max_length=240,
        help_text=_(
            "Your message. NOTE: 'Announcement: ' will be automatically be pre-pended to your message"
        ),
    )
    filter_options = forms.MultipleChoiceField(
        choices=NOTIFICATION_FILTER_CHOICES, required=False
    )
    filter_mode = forms.ChoiceField(
        default="any",
        choices=(
            ("any", _("Users with any of the above are included.")),
            ("all", _("Users with all of the above are include")),
            ("none", _("Users without any of the above are included.")),
        ),
        help_text="Adjust filter mode. Ignored if no filters selected.",
    )


class EmailForm(forms.Form):
    """
    An unbound form used for composing emails in Markdown.
    """

    subject = forms.CharField(max_length=255, help_text=_("Subject of email"))
    body = forms.Textarea(
        help_text=_("Body of your email. Use Markdown for formatting.")
    )
    filter_options = forms.MultipleChoiceField(
        choices=NOTIFICATION_FILTER_CHOICES, required=False
    )
    filter_mode = forms.ChoiceField(
        default="any",
        choices=(
            ("any", _("Users with any of the above are included.")),
            ("all", _("Users with all of the above are include")),
            ("none", _("Users without any of the above are included.")),
        ),
        help_text="Adjust filter mode. Ignored if no filters selected.",
    )
