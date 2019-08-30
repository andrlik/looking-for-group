from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import Location


class LocationForm(forms.ModelForm):
    """
    Form to embed a location lookup within a formset.
    """

    class Meta:
        model = Location
        fields = ["formatted_address", "google_place_id"]
        widgets = {"google_place_id": forms.HiddenInput}


class CityLocationForm(forms.ModelForm):
    """
    For for just specifying a city.
    """

    city = forms.CharField(
        max_length=255,
        help_text=_(
            "Enter your city and state/province. Users cannot see this information unless they are a member of your private community, one of your friends, or playing in the same game with you."
        ),
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Enter your city to help find local games."}
        ),
    )

    class Meta:
        model = Location
        fields = ["city", "google_place_id"]
        widgets = {"google_place_id": forms.HiddenInput}
