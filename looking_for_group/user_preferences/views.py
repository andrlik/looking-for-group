import logging

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic
from django_q.tasks import async_task
from notifications.models import Notification

from . import models
from ..discord import models as discord_models
from ..game_catalog import models as catalog_models
from ..gamer_profiles import models as social_models
from ..games import models as game_models

# Create your views here.


def delete_user(user):
    user.delete()


logger = logging.getLogger("gamer_profiles")


class HomeView(generic.TemplateView):
    """
    Handles making sure logged in users go to dashboard instead.
    """
    template_name = "pages/home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('dashboard'))
        return super().dispatch(request, *args, **kwargs)


class SettingsView(LoginRequiredMixin, SelectRelatedMixin, generic.DetailView):
    """
    Settings view.
    """

    model = models.Preferences
    context_object_name = "preferences"
    template_name = "user_preferences/setting_view.html"
    select_related = ["gamer"]

    def get_object(self):
        if self.request.user.is_authenticated:
            self.object, created = models.Preferences.objects.get_or_create(
                gamer=self.request.user.gamerprofile
            )
            if created:
                logger.debug("Created new record.")
            return self.object
        else:
            return None


class SettingsEdit(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Settings edit view.
    """

    model = models.Preferences
    context_object_name = "preferences"
    template_name = "user_preferences/setting_edit.html"
    fields = ["news_emails", "notification_digest", "feedback_volunteer"]
    success_url = reverse_lazy("user_preferences:setting-view")

    def get_object(self):
        self.object, created = models.Preferences.objects.get_or_create(
            gamer=self.request.user.gamerprofile
        )
        if created:
            logger.debug("Created new record.")
        return self.object


class Dashboard(LoginRequiredMixin, generic.ListView):
    """
    A dashboard view that encapsulates may different data elements.
    """

    model = Notification
    template_name = "user_preferences/dashboard.html"
    context_object_name = "notifications"

    def get_queryset(self):
        return Notification.objects.filter(unread=True, recipient=self.request.user)

    def get_context_data(self, **kwargs):
        gamer = self.request.user.gamerprofile
        context = super().get_context_data(**kwargs)
        context["friend_requests"] = social_models.GamerFriendRequest.objects.filter(
            status="new", recipient=gamer
        ).select_related("requestor")
        player_q = Q(
            id__in=[
                g.id
                for g in game_models.Player.objects.filter(gamer=gamer).exclude(
                    game__status__in=["closed", "cancel"]
                )
            ]
        )
        gm_q = Q(gm=gamer)
        context["gamer_active_games"] = (
            game_models.GamePosting.objects.filter(player_q | gm_q)
            .select_related("event")
            .prefetch_related("gamesession_set")
        )
        context["gamer_communities"] = social_models.CommunityMembership.objects.filter(
            gamer=gamer
        ).select_related("community")
        next_sessions = []
        if context["gamer_active_games"].count() > 0:
            for game in context["gamer_active_games"]:
                if game.event:
                    next_occurences = game.event.occurrences_after(timezone.now())
                    try:
                        next_sessions.append(next(next_occurences))
                    except StopIteration:
                        pass  # No next occurrence
        context["next_sessions"] = sorted(next_sessions, key=lambda k: k.start)
        context[
            "pending_community_applications"
        ] = social_models.CommunityApplication.objects.filter(
            gamer=gamer, status="pending"
        )
        context[
            "pending_game_applications"
        ] = game_models.GamePostingApplication.objects.filter(
            gamer=gamer, status="pending"
        )
        context["games_applicants"] = game_models.GamePosting.objects.exclude(
            status__in=["closed", "cancel"]
        ).filter(
            id__in=[
                g.game.id
                for g in game_models.GamePostingApplication.objects.filter(
                    game__in=game_models.GamePosting.objects.filter(gm=gamer)
                ).filter(status="pending")
            ]
        )
        comm_admin = (
            social_models.CommunityMembership.objects.filter(
                gamer=gamer, community_role="admin"
            )
            .select_related("community")
            .prefetch_related("community__communityapplication_set")
        )
        communities_and_applicant_count = []
        if comm_admin.count() > 0:
            for comm in comm_admin:
                if (
                    comm.community.communityapplication_set.filter(
                        status="pending"
                    ).count()
                    > 0
                ):
                    communities_and_applicant_count.append(comm.community)
        context["community_applicant_counts"] = communities_and_applicant_count
        context["site_total_communities"] = cache.get_or_set(
            "site_total_communities", social_models.GamerCommunity.objects.count()
        )
        context["site_total_gamers"] = cache.get_or_set(
            "site_total_gamers", social_models.GamerProfile.objects.count()
        )
        context["site_total_games"] = cache.get_or_set(
            "site_total_games", game_models.GamePosting.objects.count()
        )
        context["site_total_active_games"] = cache.get_or_set(
            "site_total_active_games",
            game_models.GamePosting.objects.exclude(
                status__in=["cancel", "closed"]
            ).count(),
        )
        context["site_total_systems"] = cache.get_or_set(
            "site_total_systems", catalog_models.GameSystem.objects.count(), 600
        )
        context["site_total_tracked_editions"] = cache.get_or_set(
            "site_total_tracked_editions",
            catalog_models.GameEdition.objects.count(),
            600,
        )
        context["site_total_publishers"] = cache.get_or_set(
            "site_total_publishers", catalog_models.GamePublisher.objects.count(), 600
        )
        context["site_total_modules"] = cache.get_or_set(
            "site_total_modules", catalog_models.PublishedModule.objects.count(), 600
        )
        context["site_total_sourcebooks"] = cache.get_or_set(
            "site_total_sourcebooks", catalog_models.SourceBook.objects.count(), 600
        )
        discord_comm_links = cache.get("site_total_discord_communities")
        if not discord_comm_links:
            discord_comm_links = 0
            dis_servers = discord_models.DiscordServer.objects.all()
            if dis_servers.count() > 0:
                comm_qs = None
                for server in dis_servers:
                    if not comm_qs:
                        comm_qs = server.communities.all()
                    else:
                        comm_qs = comm_qs.union(server.communities.all())
                if comm_qs:
                    discord_comm_links = len(comm_qs)
                else:
                    discord_comm_links = 0
            cache.set("site_total_discord_communities", discord_comm_links)
        context["site_total_discord_communities"] = discord_comm_links
        return context


class PrivacyView(generic.TemplateView):
    template_name = 'privacy.html'


class TermsView(generic.TemplateView):
    template_name = 'tos.html'


class DeleteAccount(LoginRequiredMixin, generic.DeleteView):
    """
    Deleting account view.
    """
    model = social_models.GamerProfile
    template_name = 'user_preferences/delete_account.html'
    context_object_name = 'gamer'

    def get_queryset(self):
        return self.model.objects.all().select_related('user').prefetch_related('communities', 'gmed_games', 'player_set', 'player_set__character_set')

    def get_object(self):
        queryset = self.get_queryset()
        return queryset.get(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owned_communities'] = social_models.GamerCommunity.objects.filter(owner=context['gamer'])
        return context

    def delete(self, request, *args, **kwargs):
        user = self.get_object().user
        async_task(delete_user, user)
        logout(request)
        return HttpResponseRedirect('/')
