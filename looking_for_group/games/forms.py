from django import forms
from django.utils.translation import ugettext_lazy as _

from . import models


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
            self.fields.pop('communities')
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
        ]
        widgets = {
            'start_time': forms.widgets.DateTimeInput(attrs={'class': 'dtp', 'pattern': 'simple_datetime'}),
            'end_date': forms.widgets.DateTimeInput(attrs={'class': 'dp', 'pattern': 'date', 'data-validator': 'greater_than', 'data-greater-than': 'id_start_time'}),
        }


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
        self.fields['players_missing'].required = False

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
        fields = ['scheduled_time']
        widgets = {
            'scheduled_time': forms.widgets.DateTimeInput(attrs={'class': 'dtp'})
        }
