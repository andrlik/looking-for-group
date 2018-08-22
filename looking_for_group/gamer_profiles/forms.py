from django import forms
from django.utils.translation import ugettext_lazy as _
from .models import GamerCommunity, GamerProfile


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


class BlankDistructiveForm(forms.ModelForm):
    """
    Used for post-only submissions.
    """

    class Meta:
        fields = []


class GamerProfileForm(forms.ModelForm):
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
