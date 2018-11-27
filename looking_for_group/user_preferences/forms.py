from django import forms
from django.utils.translation import ugettext_lazy as _


class DeleteAccountForm(forms.Form):
    """
    A form that takes a humanhash as an input for validation.
    """
    delete_confirm_key = forms.CharField(required=True, max_length=200, help_text=_("Enter the confirmation key as displayed above."))

    def __init__(self, *args, **kwargs):
        self.validation_key = kwargs.pop("delete_confirm_key", None)
        super().__init__(*args, **kwargs)
        if not self.validation_key:
            raise ValueError(_("You must specify the delete_confirm_key option to initialize this form!"))

    def clean(self):
        cleaned_data = super().clean()
        entered_key = cleaned_data.get("delete_confirm_key")
        if entered_key != self.validation_key:
            raise forms.ValidationError(_("You must enter your confirmation code exactly as it appears above. You may wish to use copy and paste."))
