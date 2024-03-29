from django import forms
from django.utils.translation import ugettext_lazy as _

from ..game_catalog import models as cat_models
from ..gamer_profiles.forms import BooleanSwitchPaddleFormMixin, SwitchInput
from . import models

DUMMY_CHOICES = [("", "")]


def get_edition_choices():
    return [("", "")] + [
        (e.slug, "{} ({})".format(e.game.title, e.name))
        for e in cat_models.GameEdition.objects.all()
        .select_related("game")
        .order_by("game__title", "name")
    ]


def get_system_choices():
    return [("", "")] + [
        (s.pk, s.name) for s in cat_models.GameSystem.objects.all().order_by("name")
    ]


def get_module_choices():
    return [("", "")] + [
        (m.pk, m.title)
        for m in cat_models.PublishedModule.objects.all().order_by("title")
    ]


class GamePostingForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
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
        self.fields["published_game"].queryset = self.fields[
            "published_game"
        ].queryset.order_by("game__title", "release_date", "name")

    def clean(self):
        cleaned_data = super().clean()
        if "communities" in self.fields.keys():
            communities = cleaned_data.get("communities")
            privacy = cleaned_data.get("privacy_level")
            if privacy == "private" and len(communities) > 0:
                msg = _(
                    "A game cannot be both private and posted in communities. None of your community members would be able to see it. Maximum privacy method allowed for community games is 'Friends/Selected Communities'."
                )
                self.add_error("privacy_level", msg)
                self.add_error("communities", msg)

    class Meta:
        model = models.GamePosting
        fields = [
            "game_type",
            "title",
            "status",
            "featured_image",
            "featured_image_description",
            "featured_image_cw",
            "game_mode",
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
            "start_time": forms.widgets.DateTimeInput(
                attrs={"class": "dtp"}, format="%Y-%m-%d %H:%M"
            ),
            "end_date": forms.widgets.DateTimeInput(
                attrs={"class": "dp"}, format="%Y-%m-%d"
            ),
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
    venue = forms.ChoiceField(
        choices=DUMMY_CHOICES + list(models.GAMEPLAY_MODE_CHOICES), required=False
    )
    distance = forms.ChoiceField(
        label=_("Miles from you"),
        choices=[
            ("", ""),
            (5, _("5")),
            (10, _("10")),
            (15, _("15")),
            (20, _("20")),
            (25, _("25")),
        ],
        required=False,
    )
    module = forms.ChoiceField(choices=DUMMY_CHOICES, required=False)
    similar_availability = forms.BooleanField(
        label=_("Filter by GM Sched?"),
        widget=SwitchInput(label=_("Filter by GM Sched?")),
        required=False,
    )

    def __init__(self, profile_has_city=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["filter_present"] = 1
        self.fields["edition"].choices = get_edition_choices()
        self.fields["system"].choices = get_system_choices()
        self.fields["module"].choices = get_module_choices()
        if not profile_has_city:
            self.fields["distance"].disabled = True
            self.fields["distance"].widget = forms.Select(
                attrs={
                    "title": _(
                        "You don't have your city set in your profile so distance searches cannot be done."
                    )
                }
            )


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


class AdHocGameSessionForm(GameSessionForm):
    """
    Much like the normal form except provides direct access to the scheduled_time field.
    """

    class Meta:
        model = models.GameSession
        fields = ["scheduled_time", "players_expected", "players_missing", "gm_notes"]
        widgets = {
            "scheduled_time": forms.widgets.DateTimeInput(
                attrs={"class": "dtp"}, format="%Y-%m-%d %H:%M"
            )
        }


class GameSessionCompleteUncompleteForm(forms.ModelForm):
    class Meta:
        model = models.GameSession
        fields = ["status"]


class GameSessionRescheduleForm(forms.ModelForm):
    class Meta:
        model = models.GameSession
        fields = ["scheduled_time"]
        widgets = {
            "scheduled_time": forms.widgets.DateTimeInput(
                attrs={"class": "dtp"}, format="%Y-%m-%d %H:%M"
            )
        }
