from django import forms

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
