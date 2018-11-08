from allauth.account.forms import SignupForm
from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import TIMEZONE_CHOICES


class LFGSignupForm(SignupForm):
    """
    Subclass of the ``allauth`` form to capture name of user at signup.
    """

    display_name = forms.CharField(
        label=_("Display Name"), max_length=255, required=False
    )
    timezone = forms.ChoiceField(label=_('Time Zone'), required=False, choices=TIMEZONE_CHOICES)
