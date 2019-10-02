import hashlib
import json
import logging

import factory.django
import pytz
from braces.views import SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.query_utils import Q
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django_q import humanhash
from notifications.models import Notification
from schedule.models import Calendar

from ..game_catalog import models as catalog_models
from ..gamer_profiles import models as social_models
from ..gamer_profiles.views import ModelFormWithSwitcViewhMixin
from ..games import models as game_models
from ..games.mixins import JSONResponseMixin
from . import forms, models
from .utils import fetch_or_set_discord_comm_links

# Create your views here.


logger = logging.getLogger("gamer_profiles")


def delete_user(user):
    with transaction.atomic():
        logger.debug("Delete user called, entering transaction.")
        logger.debug("Starting search for player records...")
        players = game_models.Player.objects.filter(
            gamer=user.gamerprofile
        ).select_related("gamer")
        logger.debug("Found {} player records, deleting...".format(players.count()))
        if len(players) > 0:
            for player in players:
                player.delete()
        logger.debug("Proceeding to search for gmed_games to delete...")
        games = user.gamerprofile.gmed_games.all()
        logger.debug("Found {} gmed games... deleting.".format(games.count()))
        if len(games) > 0:
            for game in games:
                with factory.django.mute_signals(pre_delete, post_delete):
                    game.event.remove_child_events()
                    game.event.delete()
                    players = game_models.Player.objects.filter(
                        game=game
                    ).select_related("gamer")
                    for player in players:
                        logger.debug(
                            "Deleting player {} from game {}".format(
                                player.gamer, game.title
                            )
                        )
                        player.delete()
                    logger.debug("Players deleted, deleting game...")
                with factory.django.mute_signals(
                    pre_delete, post_delete, m2m_changed, pre_save, post_save
                ):
                    game.delete()
        logger.debug("Games deleted, moving on.")
        try:
            logger.debug("Searching for calendar...")
            cal = Calendar.objects.get(slug=user.username)
            logger.debug("Calendar found for user, deleting...")
            cal.delete()
            logger.debug("Calendar successfully deleted.")
        except ObjectDoesNotExist:
            logger.debug("no calendar found, moving on...")
        logger.debug("Now calling delete on user object.")
        user.delete()


def generate_delete_key(user_pk):
    concat_data = ", ".join([str(timezone.now()), str(user_pk)])
    digest = hashlib.sha256(concat_data.encode())
    return humanhash.humanize(digest.hexdigest())


class HomeView(generic.TemplateView):
    """
    Handles making sure logged in users go to dashboard instead.
    """

    template_name = "pages/home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy("dashboard"))
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community_list"] = (
            social_models.CommunityMembership.objects.filter(
                gamer=self.request.user.gamerprofile
            )
            .select_related("community")
            .order_by("community__name")
        )
        return context


class SettingsEdit(
    LoginRequiredMixin, ModelFormWithSwitcViewhMixin, generic.edit.UpdateView
):
    """
    Settings edit view.
    """

    model = models.Preferences
    context_object_name = "preferences"
    template_name = "user_preferences/setting_edit.html"
    fields = [
        "news_emails",
        "notification_digest",
        "feedback_volunteer",
        "email_messages",
        "community_subscribe_default",
    ]
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
    timezone = pytz.timezone("UTC")

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.timezone
            and self.timezone != pytz.timezone(request.user.timezone)
        ):
            self.timezone = pytz.timezone(request.user.timezone)
        return super().dispatch(request, *args, **kwargs)

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
                g.game.id
                for g in game_models.Player.objects.filter(gamer=gamer).exclude(
                    game__status__in=["closed", "cancel"]
                )
            ]
        )
        gm_q = Q(gm=gamer)
        context["gamer_active_games"] = (
            game_models.GamePosting.objects.filter(
                status__in=["open", "started", "replace"]
            )
            .filter(player_q | gm_q)
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
                    next_occurences = game.event.occurrences_after(
                        timezone.now().astimezone(self.timezone)
                    )
                    try:
                        occ = next(next_occurences)
                        while occ.cancelled or occ.start < timezone.now():
                            occ = next(next_occurences)
                        next_sessions.append(occ)
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
        context["game_applicants"] = (
            game_models.GamePostingApplication.objects.filter(status="pending")
            .filter(
                game__pk__in=[
                    g.id
                    for g in game_models.GamePosting.objects.filter(gm=gamer).exclude(
                        status__in=["closed", "cancel"]
                    )
                ]
            )
            .select_related("game")
        )
        comm_admin = (
            social_models.CommunityMembership.objects.filter(
                gamer=gamer, community_role="admin"
            )
            .select_related("community")
            .prefetch_related("community__communityapplication_set")
        )
        comms_with_apps = []
        if comm_admin.count() > 0:
            for comm in comm_admin:
                if comm.community.get_pending_applications().count() > 0:
                    comms_with_apps.append(comm)
        context["comms_with_apps"] = comms_with_apps
        return context


class PrivacyView(generic.TemplateView):
    template_name = "privacy.html"


class TermsView(generic.TemplateView):
    template_name = "tos.html"


class DeleteAccount(LoginRequiredMixin, generic.DeleteView):
    """
    Deleting account view.
    """

    model = social_models.GamerProfile
    template_name = "user_preferences/delete_account.html"
    context_object_name = "gamer"
    success_url = "/"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.object = self.get_object()
            self.owned_communities = social_models.GamerCommunity.objects.filter(
                owner=self.object
            )
            self.oc_count = self.owned_communities.count()
            logger.debug(
                "Found {} communities owned by user requesting deletion.".format(
                    self.oc_count
                )
            )
            if self.oc_count > 0:
                messages.warning(
                    request,
                    _(
                        "You have {} communities for which you are the owner. You should transfer these to another admin or else these communities will be deleted for ALL USERS.".format(
                            self.oc_count
                        )
                    ),
                )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects.all()
            .select_related("user")
            .prefetch_related(
                "communities", "gmed_games", "player_set", "player_set__character_set"
            )
        )

    def get_object(self):
        queryset = self.get_queryset()
        return queryset.get(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["owned_communities"] = self.owned_communities
        context["delete_confirm_key"] = cache.get_or_set(
            "delete_confirm_key_{}".format(self.request.user.username),
            generate_delete_key(self.request.user.pk),
        )
        context["form"] = kwargs.get(
            "form",
            forms.DeleteAccountForm(delete_confirm_key=context["delete_confirm_key"]),
        )
        return context

    def delete(self, request, *args, **kwargs):
        user = self.object.user
        form = forms.DeleteAccountForm(
            request.POST,
            delete_confirm_key=cache.get_or_set(
                "delete_confirm_key_{}".format(request.user.username),
                generate_delete_key(request.user.pk),
            ),
        )
        if not form.is_valid():
            messages.error(
                request,
                _("You must confirm deletion using the confirmation key below."),
            )
            logger.debug("form invalid, sending back to user to fix.")
            return self.get(request, form=form, *args, **kwargs)
        logger.debug("Form valid, starting deletion process task.")
        logger.debug("Logging out user...")
        logout(request)
        delete_user(user)
        logger.debug("Redirecting to home.")
        return HttpResponseRedirect(self.get_success_url())


class SiteSocialStatsView(LoginRequiredMixin, JSONResponseMixin, generic.TemplateView):
    """
    Returns a JSON object containing the site stats.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logger.debug("Fetching site social stats...")
        stat_set = {
            "site_total_communities": cache.get_or_set(
                "site_total_communities", social_models.GamerCommunity.objects.count()
            ),
            "site_total_gamers": cache.get_or_set(
                "site_total_gamers", social_models.GamerProfile.objects.count()
            ),
            "site_total_games": cache.get_or_set(
                "site_total_games",
                game_models.GamePosting.objects.exclude(status="cancel").count(),
            ),
            "site_total_active_games": cache.get_or_set(
                "site_total_active_games",
                game_models.GamePosting.objects.exclude(
                    status__in=["cancel", "closed"]
                ).count(),
            ),
            "site_total_completed_sessions": cache.get_or_set(
                "site_total_completed_sessions",
                game_models.GameSession.objects.filter(status="complete").count(),
            ),
            "site_total_discord_communities": fetch_or_set_discord_comm_links(),
        }
        logger.debug("Stats fetched. Returning to context.")
        context["stat_set"] = stat_set
        return context

    def get_data(self, context):
        return context["stat_set"]


class SiteCatalogStatsView(LoginRequiredMixin, JSONResponseMixin, generic.TemplateView):
    """
    Returns a JSON response containing the catalog stats
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stat_set = {
            "site_total_systems": cache.get_or_set(
                "site_total_systems", catalog_models.GameSystem.objects.count()
            ),
            "site_total_tracked_editions": cache.get_or_set(
                "site_total_tracked_editions",
                catalog_models.GameEdition.objects.count(),
            ),
            "site_total_publishers": cache.get_or_set(
                "site_total_publishers", catalog_models.GamePublisher.objects.count()
            ),
            "site_total_modules": cache.get_or_set(
                "site_total_modules", catalog_models.PublishedModule.objects.count()
            ),
            "site_total_sourcebooks": cache.get_or_set(
                "site_total_sourcebooks", catalog_models.SourceBook.objects.count()
            ),
        }
        context["stat_set"] = stat_set
        logger.debug("Sending {}".format(stat_set))
        return context

    def get_data(self, context):
        return context["stat_set"]
