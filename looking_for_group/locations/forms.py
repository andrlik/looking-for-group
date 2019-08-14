from django import forms

from .models import Location


class LocationForm(forms.ModelForm):
    """
    Form to embed a location lookup within a formset.
    """

    class Meta:
        model = Location
        fields = ["formatted_address", "google_place_id"]
        widgets = {"google_place_id": forms.HiddenInput}
