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
        fields = ['reason', 'end_date']
        widgets = {'end_date': forms.widgets.DateInput(attrs={'class': 'dp'})}


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


class CommunityDiscordForm(forms.ModelForm):
    """
    A form for linking/unlinking communites from discord servers.
    """

    def __init__(self, *args, **kwargs):
        linkable_servers_qs = kwargs.pop('linkable_servers_queryset', None)
        if not linkable_servers_qs:
            raise KeyError(_('Must provide queryset of linkable servers.'))
        super().__init__(*args, **kwargs)
        self.fields['servers'].queryset = DiscordServer.objects.filter(id__in=[s.server.id for s in linkable_servers_qs])

    class Meta:
        model = CommunityDiscordLink
        fields = ['servers']
