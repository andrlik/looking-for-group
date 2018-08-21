from django import forms
from django.utils.translation import ugettext_lazy as _
from .models import GamerCommunity


class OwnershipTransferForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        community = kwargs.pop("community", None)
        super().__init__(*args, **kwargs)
        if community:
            self.fields["owner"].queryset = community.get_admins()
        else:
            raise KeyError(_("Community must be specified!"))  # pragma: no cover

    class Meta:
        model = GamerCommunity
        fields = ["owner"]


class BlankDistructiveForm(forms.ModelForm):
    """
    Used for post-only submissions.
    """

    class Meta:
        fields = []
