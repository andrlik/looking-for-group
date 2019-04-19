from django import forms
from django.utils.translation import ugettext_lazy as _
from . import models


class BookForm(forms.ModelForm):
    """
    For for editing a book in a collection.
    """

    def clean(self):
        cleaned_data = super().clean()
        in_print = cleaned_data.get("in_print")
        in_pdf = cleaned_data.get("in_pdf")

        if not in_print and not in_pdf:
            raise forms.ValidationError(_("You must select one or both for Print or PDF."))

    class Meta:
        model = models.Book
        fields = ["object_id", "in_print", "in_pdf"]
        widgets = {
            "object_id": forms.HiddenInput,
        }
