from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from ...discord.models import CommunityDiscordLink, DiscordServer, DiscordServerMembership, GamerDiscordLink
from ..forms import CommunityDiscordForm
from ..models import GamerCommunity


class CommunityDiscordLinkView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    A view designed to allow a user to connect a community to a given discord server.
    """

    model = CommunityDiscordLink
    slug_url_kwarg = "community"
    slug_field = "slug"
    permission_required = "community.edit_community"
    template_name = "gamer_profiles/community_discord_link.html"
    context_object_name = "community_discord_link"
    form_class = CommunityDiscordForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.community = get_object_or_404(GamerCommunity, slug=kwargs["community"])
            if self.community.linked_to_discord:
                messages.info(
                    request, _("This community is already linked to a discord server.")
                )
            # Find the social app connection.
            try:
                self.discord_link = GamerDiscordLink.objects.get(
                    gamer=request.user.gamerprofile
                )
                self.linkable_servers = DiscordServerMembership.objects.filter(
                    gamer_link=self.discord_link, server_role="admin"
                )
                if self.linkable_servers.count() == 0:
                    messages.info(
                        request,
                        _(
                            "No linkable Discord servers have been synced with your account yet. You must be an admin for the Discord server in order to link it to a community on this site."
                        ),
                    )
            except ObjectDoesNotExist:
                messages.info(
                    request,
                    _(
                        "In order to manage Discord links for this community, you must first authenticate with Discord to prove you have the ability to do so."
                    ),
                )
                return HttpResponseRedirect(reverse_lazy("socialaccount_connections"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        self.community_discord_link, created = CommunityDiscordLink.objects.get_or_create(
            community=self.community
        )
        return self.community_discord_link

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community"] = self.community
        context["discord_gamer_link"] = self.discord_link
        context["linkable_servers"] = self.linkable_servers
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super().get_form_kwargs(**kwargs)
        form_kwargs["linkable_servers_queryset"] = self.linkable_servers
        return form_kwargs

    def form_valid(self, form):
        with transaction.atomic:
            immutable_servers = list(
                self.community_discord_link.servers.exclude(
                    id__in=[s.id for s in self.linkable_servers.all()]
                )
            )
            temp_obj = form.save(commit=False)
            new_list = (
                list(
                    DiscordServer.objects.filter(
                        id__in=[s.id for s in temp_obj.servers.all()]
                    )
                )
                + immutable_servers
            )
            if len(new_list) > 0:
                if not self.community.linked_to_discord:
                    self.community.linked_to_discord = True
                    self.community.save()
                self.community_discord_link.servers.set(*new_list)
            else:
                if self.community.linked_to_discord:
                    self.community.linked_to_discord = False
                    self.community.save()
                self.community_discord_link.servers.clear()
            messages.success(self.request, _("Changes have been successfully saved!"))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.community.get_absolute_url()
