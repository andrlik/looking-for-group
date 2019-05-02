from django import forms
from django.utils.translation import ugettext_lazy as _

from ..gamer_profiles.forms import BooleanSwitchPaddleFormMixin
from . import models


class GameForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    Game form
    """

    class Meta:
        model = models.PublishedGame
        fields = ["title", "image", "url", "description", "publication_date", "tags"]
        widgets = {"publication_date": forms.widgets.DateInput(attrs={"class": "dp"}, format="%Y-%m-%d")}


class SystemForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    Game system form
    """

    class Meta:
        model = models.GameSystem
        fields = [
            "name",
            "image",
            "system_url",
            "description",
            "original_publisher",
            "ogl_license",
            "publication_date",
            "tags",
        ]
        widgets = {"publication_date": forms.widgets.DateInput(attrs={"class": "dp"}, format="%Y-%m-%d")}


class EditionForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    Game edition form.
    """

    class Meta:
        model = models.GameEdition
        fields = [
            "name",
            "game_system",
            "image",
            "url",
            "publisher",
            "release_date",
            "description",
            "url",
            "tags",
        ]
        widgets = {"release_date": forms.widgets.DateInput(attrs={"class": "dp"}, format="%Y-%m-%d")}


class SourceBookForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    Form for sourcebook.
    """

    class Meta:
        model = models.SourceBook
        fields = ["title", "image", "corebook", "publisher", "release_date", "isbn", "tags"]
        widgets = {"release_date": forms.widgets.DateInput(attrs={"class": "dp"}, format="%Y-%m-%d")}


class ModuleForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    Form for modules
    """

    class Meta:
        model = models.PublishedModule
        fields = [
            "title",
            "image",
            "url",
            "publisher",
            "publication_date",
            "isbn",
            "tags",
        ]
        widgets = {"publication_date": forms.widgets.DateInput(attrs={"class": "dp"}, format="%Y-%m-%d")}


class SuggestedCorrectionForm(forms.ModelForm):
    """
    A form for suggested corrections
    """
    pass


class SuggestedAdditionForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    A form for suggested additions.
    """

    object_type = None

    def __init__(self, *args, **kwargs):
        obj_type = kwargs.pop("obj_type", None)
        if not obj_type or obj_type not in ["game", "publisher", "edition", "system", "sourcebook", "module"]:
            raise KeyError(_("You must specify an object type!"))
        self.object_type = obj_type
        super().__init__(*args, **kwargs)
        if obj_type in ["sourcebook", "module"]:
            self.fields['description'].widget = forms.HiddenInput()
        if obj_type in ["game", "publisher"]:
            self.fields['release_date'].widget = forms.HiddenInput()
            self.fields['publisher'].widget = forms.HiddenInput()
        if obj_type != "system":
            self.fields['ogl_license'].widget = forms.HiddenInput()
        if obj_type not in ["sourcebook", "module", "system"]:
            self.fields['isbn'].widget = forms.HiddenInput()
        if obj_type not in ["sourcebook", "module"]:
            self.fields["edition"].widget = forms.HiddenInput()
        if obj_type != "edition":
            self.fields["system"].widget = forms.HiddenInput()
            self.fields["game"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        game = cleaned_data.get("game")
        publisher = cleaned_data.get("publisher")
        edition = cleaned_data.get("edition")
        if self.object_type in ["system", "edition", "module", "sourcebook"]:
            if not publisher:
                self.add_error("publisher", _("You must specify a publisher for this object type."))
            if self.object_type in ["module", "sourcebook"]:
                if not edition:
                    self.add_error("edition", _("You must specify a game edition for this object."))
            if self.object_type == "edition" and not game:
                self.add_error("game", _("You need to specify the game for which this is an edition."))
        return cleaned_data

    class Meta:
        model = models.SuggestedAddition
        fields = [
            "title",
            "image",
            "url",
            "description",
            "release_date",
            "isbn",
            "ogl_license",
            "publisher",
            "game",
            "edition",
            "system",
            "suggested_tags",
        ]
        widgets = {
            "release_date": forms.widgets.DateInput(attrs={"class": "dp"}, format="%Y-%m-%d"),
        }
