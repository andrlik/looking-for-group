from django import forms
from django.utils.translation import ugettext_lazy as _

from . import models
from ..game_catalog import models as cat_models

DUMMY_CHOICES = [("", "")]


def get_edition_choices():
    return [("", "")] + [(e.slug, "{} ({})".format(e.game.title, e.name)) for e in cat_models.GameEdition.objects.all().select_related("game").order_by("game__title", "name")]


def get_system_choices():
    return [("", "")] + [(s.pk, s.name) for s in cat_models.GameSystem.objects.all().order_by('name')]


def get_module_choices():
    return [("", "")] + [(m.pk, m.title) for m in cat_models.PublishedModule.objects.all().order_by('title')]


class GamePostingForm(forms.ModelForm):
    """
    A form representing the GamePosting. Essentially just to
    limit community posting choices.
    """

    def __init__(self, *args, **kwargs):
        gamer = kwargs.pop("gamer", False)
        if not gamer:
            raise KeyError(_("You must instantiate this form with a gamer profile"))
        allowed_communities = gamer.communities.all()
        super().__init__(*args, **kwargs)
        if allowed_communities.count() == 0:
            self.fields.pop("communities")
        if "communities" in self.fields.keys():
            self.fields["communities"].queryset = allowed_communities

    class Meta:
        model = models.GamePosting
        fields = [
            "game_type",
            "title",
            "min_players",
            "max_players",
            "adult_themes",
            "content_warning",
            "privacy_level",
            "game_system",
            "published_game",
            "published_module",
            "game_frequency",
            "start_time",
            "session_length",
            "end_date",
            "game_description",
            "communities",
            "tags",
        ]
        widgets = {
            "start_time": forms.widgets.DateTimeInput(attrs={"class": "dtp"}),
            "end_date": forms.widgets.DateTimeInput(attrs={"class": "dp"}),
        }


class GameFilterForm(forms.Form):
    """
    A form for filtering game listings.
    """

    filter_present = forms.HiddenInput()
    game_status = forms.ChoiceField(
        choices=[("", "")] + models.GAME_STATUS_CHOICES, initial="", required=False
    )
    edition = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    system = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    module = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["filter_present"] = 1
        self.fields['edition'].choices = get_edition_choices()
        self.fields['system'].choices = get_system_choices()
        self.fields['module'].choices = get_module_choices()


class GameSessionForm(forms.ModelForm):
    """
    Restricts player options to those involved in Game.
    """

    def __init__(self, *args, **kwargs):
        game = kwargs.pop("game", False)
        if not game:
            raise KeyError(_("A game must be specified in order to create a session."))
        super().__init__(*args, **kwargs)
        game_players = models.Player.objects.filter(game=game)
        self.fields["players_expected"].queryset = game_players
        self.fields["players_missing"].queryset = game_players
        self.fields["players_missing"].required = False

    def clean(self):
        cleaned_data = super().clean()
        players_expected = cleaned_data.get("players_expected")
        players_missing = cleaned_data.get("players_missing")
        if players_missing:
            for player in players_missing:
                if not players_expected or player not in players_expected:
                    raise forms.ValidationError(
                        _(
                            "You cannot list a player as missing if they were not also expected for this session."
                        )
                    )

    class Meta:
        model = models.GameSession
        fields = ["players_expected", "players_missing", "gm_notes"]


class GameSessionRescheduleForm(forms.ModelForm):
    class Meta:
        model = models.GameSession
        fields = ["scheduled_time"]
        widgets = {
            "scheduled_time": forms.widgets.DateTimeInput(attrs={"class": "dtp"})
        }
