from django import forms
from django.utils.translation import ugettext_lazy as _

from ..discord.models import CommunityDiscordLink, DiscordServer
from .models import GamerCommunity, GamerProfile, KickedUser


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


class SwitchInput(forms.widgets.CheckboxInput):

    template_name = "gamer_profiles/switch_control.html"
    wrap_label = True
    label = None

    def __init__(self, label=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if label:
            self.label = label
        try:
            self.attrs["class"] = "{} switch-input".format(self.attrs["class"])
        except KeyError:
            self.attrs["class"] = "switch-input"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if not self.label:
            context["widget"]["label"] = name.replace("_", " ").title()
        else:
            context["widget"]["label"] = self.label
        return context


class BooleanSwitchPaddleFormMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.fields.items():
            if isinstance(value, forms.BooleanField):
                value.widget = SwitchInput()


class ModelFormWithSwitchPaddles(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    pass


class BlankDistructiveForm(forms.ModelForm):
    """
    Used for post-only submissions.
    """

    class Meta:
        fields = []


class KickUserForm(forms.ModelForm):
    """
    Used for kicking a single user.
    """

    class Meta:
        model = KickedUser
        fields = ["reason", "end_date"]
        widgets = {"end_date": forms.widgets.DateInput(attrs={"class": "dp"})}


class GamerProfileForm(BooleanSwitchPaddleFormMixin, forms.ModelForm):
    """
    A profile form that will typically be populated with the userform.
    Note: Default profiles are created automatically, so this can only
    be used for updating an existing instance.
    """

    class Meta:
        model = GamerProfile
        fields = (
            "private",
            "rpg_experience",
            "ttgame_experience",
            "playstyle",
            "player_status",
            "will_gm",
            "adult_themes",
            "one_shots",
            "adventures",
            "campaigns",
            "online_games",
            "local_games",
            "preferred_games",
            "preferred_systems",
        )


class CommunityDiscordForm(forms.ModelForm):
    """
    A form for linking/unlinking communites from discord servers.
    """

    def __init__(self, *args, **kwargs):
        linkable_servers_qs = kwargs.pop("linkable_servers_queryset", None)
        if not linkable_servers_qs:
            raise KeyError(_("Must provide queryset of linkable servers."))
        super().__init__(*args, **kwargs)
        self.fields["servers"].queryset = DiscordServer.objects.filter(
            id__in=[s.server.id for s in linkable_servers_qs]
        )

    class Meta:
        model = CommunityDiscordLink
        fields = ["servers"]


class GamerAvailabilityForm(forms.Form):
    """
    A form for setting availability for a given date.
    """

    monday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    monday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    monday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    tuesday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    tuesday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    tuesday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    wednesday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    wednesday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    wednesday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    thursday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    thursday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    thursday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    friday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    friday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    friday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    saturday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    saturday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    saturday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    sunday_all_day = forms.BooleanField(
        required=False,
        widget=SwitchInput(),
        help_text=_("Use this instead of time fields if available all day"),
    )
    sunday_earliest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )
    sunday_latest = forms.TimeField(
        required=False,
        widget=forms.widgets.TimeInput(attrs={"pattern": "time"}),
        help_text=_("(hh:mm) Leave blank if not available."),
    )

    def clean(self):
        cleaned_data = super().clean()
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            try:
                if not cleaned_data["{}_all_day".format(day)] and (
                    (
                        cleaned_data["{}_earliest".format(day)]
                        and not cleaned_data["{}_latest".format(day)]
                    )
                    or (
                        not cleaned_data["{}_earliest".format(day)]
                        and cleaned_data["{}_latest".format(day)]
                    )
                ):
                    self.add_error(
                        "{}_earliest".format(day),
                        forms.ValidationError(
                            _(
                                "If specifying a value for a day, you must choose either all day or specify both an earliest and latest time."
                            )
                        ),
                    )
                if (
                    not cleaned_data["{}_all_day".format(day)]
                    and cleaned_data["{}_earliest".format(day)]
                    and cleaned_data["{}_latest".format(day)]
                    and cleaned_data["{}_earliest".format(day)]
                    > cleaned_data["{}_latest".format(day)]
                ):
                    self.add_error(
                        "{}_earliest".format(day),
                        forms.ValidationError(
                            _("Earliest time must be before latest time.")
                        ),
                    )
            except KeyError:
                pass  # Field did not validate to begin with.
