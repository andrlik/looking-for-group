import datetime
import logging
import urllib

import pytz
from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.measure import Distance
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.db.models.query_utils import Q
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from notifications.signals import notify
from rest_framework.renderers import JSONRenderer
from rules.contrib.views import PermissionRequiredMixin
from schedule.models import Calendar, Occurrence
from schedule.periods import Day, Month

from . import forms, models, serializers
from ..game_catalog.models import GameEdition, GameSystem, PublishedModule
from ..gamer_profiles.models import GamerProfile
from ..locations.forms import LocationForm
from ..locations.models import Location
from .mixins import JSONResponseMixin
from .signals import player_kicked, player_left
from .utils import mkfirstOfmonth, mkLastOfMonth

# Create your views here.

logger = logging.getLogger("games")


class GameListAbstractView(
    LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView
):
    """
    A generic view that can be used to load the game lists and handle all the filtering.
    """

    model = models.GamePosting
    select_related = ["game_system", "published_game", "published_module", "gm"]
    prefetch_related = ["players", "communities"]
    paginate_by = 15
    context_object_name = "game_list"
    paginate_orphans = 3
    is_filtered = False
    filter_game_status = None
    filter_edition = None
    filter_system = None
    filter_module = None
    filter_availability = None
    filter_querystring = None
    filter_venue = None
    filter_distance = None
    stub_queryset = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_filterd"] = self.is_filtered
        context["querystring"] = self.filter_querystring
        has_city = False
        if (
            self.request.user.gamerprofile.city
            and self.request.user.gamerprofile.city.is_geocoded
        ):
            has_city = True
        if self.is_filtered:
            filter_form = forms.GameFilterForm(
                profile_has_city=has_city,
                initial={
                    "game_status": self.filter_game_status,
                    "edition": self.filter_edition,
                    "system": self.filter_system,
                    "module": self.filter_module,
                    "similar_availability": self.filter_availability,
                    "venue": self.filter_venue,
                    "distance": self.filter_distance,
                },
            )
        else:
            filter_form = forms.GameFilterForm(profile_has_city=has_city)
        context["filter_form"] = filter_form
        return context

    def get_stub_queryset(self):
        if not self.stub_queryset:
            gamer = self.request.user.gamerprofile
            friends = gamer.friends.all()
            communities = [f.id for f in gamer.communities.all()]
            game_player_ids = [
                obj.game.id
                for obj in models.Player.objects.filter(gamer=gamer).select_related(
                    "game"
                )
            ]
            q_gm = Q(gm=gamer)
            q_gm_is_friend = Q(gm__in=friends) & Q(privacy_level="community")
            q_isplayer = Q(id__in=game_player_ids)
            q_community = Q(communities__id__in=communities) & Q(
                privacy_level="community"
            )
            q_public = Q(privacy_level="public")
            self.stub_queryset = models.GamePosting.objects.filter(
                q_gm | q_public | q_gm_is_friend | q_isplayer | q_community
            ).distinct()
        return self.stub_queryset

    def handle_form_filters(self, queryset):
        get_dict = self.request.GET.copy()
        query_string_data = {}
        if get_dict.pop("filter_present", None):
            self.filter_game_status = get_dict.pop("game_status", None)
            edition = get_dict.pop("edition", None)
            system = get_dict.pop("system", None)
            print(system)
            module = get_dict.pop("module", None)
            self.filter_venue = get_dict.pop("venue", None)
            if self.filter_venue and self.filter_venue[0] != "":
                self.is_filtered = True
                queryset = queryset.filter(game_mode=self.filter_venue[0])
                query_string_data["venue"] = self.filter_venue[0]
                if self.filter_venue[0] == "irl":
                    if (
                        self.request.user.gamerprofile.city
                        and self.request.user.gamerprofile.city.is_geocoded
                    ):
                        self.filter_distance = get_dict.pop("distance", None)
                        if self.filter_distance and self.filter_distance[0] != "":
                            queryset = queryset.filter(
                                game_location__latlong__distance_lte=(
                                    self.request.user.gamerprofile.city.latlong,
                                    Distance(mi=self.filter_distance[0]),
                                )
                            )
                            query_string_data["distance"] = self.filter_distance[0]
                    else:
                        messages.info(
                            self.request,
                            _(
                                "You are searching for a face-to-face game, but you don't have a city in your profile, so we won't be able to provide distance based searches. However, all face-to-face games matching your other criteria are displayed below."
                            ),
                        )
            if self.filter_game_status and self.filter_game_status[0] != "":
                self.is_filtered = True
                queryset = queryset.filter(status=self.filter_game_status[0])
                query_string_data["game_status"] = self.filter_game_status[0]
            if edition and edition[0] != "":
                query_string_data["edition"] = edition[0]
                self.is_filtered = True
                try:
                    ed = GameEdition.objects.get(slug=edition[0])
                    queryset = queryset.filter(published_game=ed)
                    self.filter_edition = ed.slug
                except ObjectDoesNotExist:
                    pass
            if system and system[0] != "":
                query_string_data["system"] = system[0]
                self.is_filtered = True
                try:
                    sys_obj = GameSystem.objects.get(pk=system[0])
                    queryset = queryset.filter(game_system=sys_obj)
                    self.filter_system = sys_obj.pk
                except ObjectDoesNotExist:
                    pass
            if module and module[0] != "":
                query_string_data["module"] = module[0]
                self.is_filtered = True
                try:
                    mod_obj = PublishedModule.objects.get(pk=module[0])
                    queryset = queryset.filter(published_module=mod_obj)
                    self.filter_module = mod_obj.pk
                except ObjectDoesNotExist:
                    pass
            if query_string_data:
                self.filter_querystring = urllib.parse.urlencode(query_string_data)
        return queryset

    def get_queryset(self):
        return self.handle_form_filters(
            self.get_stub_queryset()
            .exclude(status__in=["cancel", "closed"])
            .order_by("-modified")
        )


class GamePostingListView(GameListAbstractView):
    """
    A generic list view for game postings.
    """

    template_name = "games/game_list.html"


class MyGameList(GameListAbstractView):
    """
    A list for games that the current user is involved with.
    """

    template_name = "games/my_game_list.html"
    context_object_name = "active_game_list"

    def get_stub_queryset(self):
        if not self.stub_queryset:
            gamer = self.request.user.gamerprofile
            game_player_ids = [
                obj.game.id
                for obj in models.Player.objects.filter(gamer=gamer).select_related(
                    "game"
                )
            ]
            q_gm = Q(gm=gamer)
            q_is_player = Q(id__in=game_player_ids)
            self.stub_queryset = models.GamePosting.objects.filter(q_gm | q_is_player)
        return self.stub_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["completed_game_list"] = self.handle_form_filters(
            self.get_stub_queryset()
            .filter(status__in=["cancel", "closed"])
            .order_by("-modified")
        )
        context[
            "pending_game_application_count"
        ] = models.GamePostingApplication.objects.filter(
            gamer=self.request.user.gamerprofile, status="pending"
        )
        return context


class GamePostingCreateView(LoginRequiredMixin, generic.CreateView):
    """
    Create view for game posting.
    """

    models = models.GamePosting
    form_class = forms.GamePostingForm
    template_name = "games/game_create.html"
    allowed_communities = None

    def get_allowed_communties(self):
        if not self.allowed_communities:
            self.allowed_communities = self.request.user.gamerprofile.communities.all()
        return self.allowed_communities

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["allowed_communities"] = self.get_allowed_communties()
        if self.request.POST:
            location_form = LocationForm(self.request.POST, prefix="location")
        else:
            location_form = LocationForm(prefix="location")
        context["location_form"] = location_form
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["gamer"] = self.request.user.gamerprofile
        return kwargs

    def form_valid(self, form):
        self.game_posting = form.save(commit=False)
        self.game_posting.gm = self.request.user.gamerprofile
        if self.game_posting.communities:
            for comm in self.game_posting.communities.all():
                if comm not in self.get_allowed_communties():
                    messages.error(
                        self.request,
                        _(
                            "You do not have permission to post games into community {}".format(
                                comm.name
                            )
                        ),
                    )
                    return self.form_invalid(form)
        location_form = LocationForm(self.request.POST, prefix="location")
        if (
            self.game_posting.game_mode == "irl"
            and location_form.is_valid()
            and (
                location_form.cleaned_data["google_place_id"]
                or location_form.cleaned_data["formatted_address"]
            )
        ):
            if location_form.cleaned_data["google_place_id"]:
                game_location, created = Location.objects.get_or_create(
                    google_place_id=location_form.cleaned_data["google_place_id"],
                    defaults={
                        "formatted_address": location_form.cleaned_data[
                            "formatted_address"
                        ]
                    },
                )
            else:
                game_location, created = Location.objects.get_or_create(
                    formatted_address=location_form.cleaned_data["formatted_address"]
                )
            game_location.geocode()
            if not game_location.is_geocoded:
                messages.error(
                    "Your game was saved, but we were not able to locate the address you specified for the game, and so it was omitted."
                )
            else:
                self.game_posting.game_location = game_location
        self.game_posting.save()
        self.game_posting.gm.games_created = F("gamed_created") + 1
        return HttpResponseRedirect(reverse_lazy("games:game_list"))


class GamePostingDetailView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    Detail view for a game posting.
    """

    model = models.GamePosting
    select_related = [
        "event",
        "published_game",
        "game_system",
        "published_module",
        "gamesession_set",
        "gamesession_set__adventurelog",
    ]
    prefetch_related = ["players", "communities"]
    permission_required = "game.can_view_listing"
    template_name = "games/game_detail.html"
    slug_url_kwarg = "gameid"
    slug_field = "slug"
    context_object_name = "game"

    def dispatch(self, request, *args, **kwargs):
        self.game = self.get_object()
        if (
            request.user.is_authenticated
            and request.user.gamerprofile not in self.game.players.all()
            and request.user.gamerprofile != self.game.gm
        ):
            return HttpResponseRedirect(
                reverse_lazy("games:game_apply", kwargs={"gameid": self.game.slug})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_list = models.GameSession.objects.filter(
            game=self.game, status__in=["pending", "complete"]
        ).order_by("-scheduled_time")
        if session_list.count() > 5:
            context["recent_sessions"] = session_list[:5]
        else:
            context["recent_sessions"] = session_list
        context["player_list"] = models.Player.objects.filter(game=self.game).order_by(
            "gamer__username"
        )
        context[
            "pending_applicant_list"
        ] = models.GamePostingApplication.objects.filter(
            status="pending", game=self.game
        )
        return context

    def get_queryset(self):
        return models.GamePosting.objects.all()


class GamePostingApplyView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    View for managing applying to a game.
    """

    model = models.GamePostingApplication
    template_name = "games/game_apply.html"
    permission_required = "game.can_apply"
    fields = ["message"]

    def dispatch(self, request, *args, **kwargs):
        game_slug = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        if request.user.is_authenticated:
            if (
                request.user.gamerprofile in self.game.players.all()
                or request.user.gamerprofile == self.game.gm
            ):
                return HttpResponseRedirect(self.game.get_absolute_url())
            if (
                models.GamePostingApplication.objects.filter(
                    game=self.game, gamer=request.user.gamerprofile, status="pending"
                ).count()
                > 0
            ):
                messages.info(
                    request, _("You already have an active application for this game.")
                )
                return HttpResponseRedirect(reverse_lazy("games:my-game-applications"))
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def form_valid(self, form):
        application = form.save(commit=False)
        if "submit_app" in self.request.POST.keys():
            application.status = "pending"
        application.gamer = self.request.user.gamerprofile
        application.game = self.game
        application.save()
        if application.status == "pending":
            notify.send(
                self.request.user.gamerprofile,
                recipient=self.game.gm.user,
                verb="submitted application",
                action_object=application,
                target=self.game,
            )
        return HttpResponseRedirect(application.get_absolute_url())


class GamePostingApplicationDetailView(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.DetailView
):
    """
    View for an application detail.
    """

    model = models.GamePostingApplication
    context_object_name = "application"
    select_related = ["game", "gamer"]
    slug_url_kwarg = "application"
    slug_field = "slug"
    permission_required = "game.view_application"
    template_name = "games/game_apply_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["application"].game
        return context


class GamePostingApplicationUpdateView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Update view for a game application.
    """

    model = models.GamePostingApplication
    slug_url_kwarg = "application"
    select_related = ["game"]
    slug_field = "slug"
    permission_required = "game.edit_application"
    context_object_name = "application"
    template_name = "games/game_apply_update.html"
    fields = ["message"]

    def dispatch(self, request, *args, **kwargs):
        self.application = self.get_object()
        if (
            request.user.is_authenticated
            and request.user.gamerprofile == self.application.gamer
            and self.application.status not in ["new", "pending"]
        ):
            messages.error(
                request,
                _("This application has been processed and can no longer be edited."),
            )
            return HttpResponseRedirect(self.application.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_object().get_absolute_url()

    def form_valid(self, form):
        if "submit_app" in self.request.POST.keys():
            form.instance.status = "pending"
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["application"].game
        return context


class GamePostingWithdrawApplication(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for an application.
    """

    model = models.GamePostingApplication
    template_name = "games/game_apply_delete.html"
    permission_required = "game.edit_application"
    select_related = ["game"]
    context_object_name = "application"
    slug_url_kwarg = "application"

    def get_success_url(self):
        if self.object.status == "pending":
            notify.send(
                self.request.user.gamerprofile,
                recipient=self.object.game.gm.user,
                verb="withdrew their application",
                target=self.object.game,
            )
        return self.object.game.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["application"].game
        return context


class GamePostingAppliedList(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):
    """
    View of a user's personal application list.
    """

    select_related = ["game"]
    template_name = "games/game_application_list.html"
    model = models.GamePostingApplication
    context_object_name = "application_list"

    def get_queryset(self):
        self.model.objects.filter(
            gamer=self.request.user.gamerprofile, status__in=("new", "pending")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approved_application_list"] = self.model.objects.filter(
            gamer=self.request.user.gamerprofile, status="approve"
        )
        context["rejected_application_list"] = self.model.objects.filter(
            gamer=self.request.user.gamerprofile, status="deny"
        )
        return context


class GamePostingApplicantList(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.ListView
):
    """
    GM view of gamers that have applied to game.
    """

    model = models.GamePostingApplication
    select_related = ["gamer", "game"]
    context_object_name = "applicants"
    permission_required = "game.can_edit_listing"
    template_name = "games/game_applicant_list.html"

    def dispatch(self, request, *args, **kwargs):
        game_slug = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_queryset(self):
        return self.model.objects.filter(game=self.game, status="pending")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["approved_applicants"] = (
            self.model.objects.filter(game=self.game, status="approve")
            .select_related("gamer")
            .order_by("-modified")
        )
        context["rejected_applicants"] = (
            self.model.objects.filter(game=self.game, status="deny")
            .select_related("gamer")
            .order_by("-modified")
        )
        context["game"] = self.game
        return context


class GamePostingApplicationApproveReject(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Approve a game applicant.
    """

    model = models.GamePostingApplication
    permission_required = "game.can_edit_listing"
    fields = ["status"]
    slug_url_kwarg = "application"

    def get_permission_object(self):
        return self.get_object().game

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() != "post":
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        if obj.status not in ["approve", "deny"]:
            raise PermissionDenied  # Someone is manually editing form date to create shenanigans
        if obj.status == "approve":
            with transaction.atomic():
                obj.save()
                models.Player.objects.create(gamer=obj.gamer, game=obj.game)
                messages.success(
                    self.request,
                    _(
                        "You have approved the player application for {}".format(
                            obj.gamer
                        )
                    ),
                )
        else:
            obj.save()
            notify.send(
                obj,
                recipient=obj.gamer.user,
                verb="Your player application was not accepted",
                action_object=obj,
                target=obj.game,
            )
        return HttpResponseRedirect(
            reverse_lazy("games:game_applicant_list", kwargs={"gameid": obj.game.slug})
        )


class GamePostingUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a game posting.
    """

    model = models.GamePosting
    permission_required = "game.can_edit_listing"
    template_name = "games/game_update.html"
    form_class = forms.GamePostingForm
    slug_url_kwarg = "gameid"
    slug_field = "slug"
    allowed_communities = None
    context_object_name = "game"

    def get_success_url(self):
        return self.get_object().get_absolute_url()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["gamer"] = self.request.user.gamerprofile
        return kwargs

    def get_allowed_communities(self):
        if not self.allowed_communities:
            self.allowed_communities = self.request.user.gamerprofile.communities.all()
        return self.allowed_communities

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["allowed_communities"] = self.get_allowed_communities()
        if self.request.POST:
            context["location_form"] = LocationForm(
                self.request.POST,
                prefix="location",
                instance=context["game"].game_location,
            )
        else:
            context["location_form"] = LocationForm(
                prefix="location", instance=context["game"].game_location
            )
        return context

    def form_valid(self, form):
        prev_version = self.get_object()
        obj_to_save = form.save(commit=False)
        if obj_to_save.game_mode == "irl":
            logger.debug("This is an IRL game. Checking for supplied address.")
            location_form = LocationForm(self.request.POST, prefix="location")
            if location_form.is_valid():
                if (
                    not location_form.cleaned_data["formatted_address"]
                    or location_form.cleaned_data["formatted_address"] == ""
                ):
                    logger.debug("Address is not present, clearing location.")
                    obj_to_save.game_location = None
                else:
                    if (
                        not prev_version.game_location
                        or location_form.cleaned_data["google_place_id"]
                        != prev_version.game_location.google_place_id
                    ):
                        if location_form.cleaned_data["google_place_id"]:
                            location, created = Location.objects.get_or_create(
                                google_place_id=location_form.cleaned_data[
                                    "google_place_id"
                                ],
                                defaults={
                                    "formatted_address": location_form.cleaned_data[
                                        "formatted_address"
                                    ]
                                },
                            )
                        else:
                            location, created = Location.objects.get_or_create(
                                formatted_address=location_form.cleaned_data[
                                    "formatted_address"
                                ]
                            )
                        if created or not location.is_geocoded:
                            location.geocode()
                        if not location.is_geocoded:
                            messages.error(
                                _(
                                    "We could not locate the address you specified so it has not been changed."
                                )
                            )
                        else:
                            logger.debug("Updating location association for game.")
                            obj_to_save.game_location = location
        if prev_version.status != obj_to_save.status and "closed" in [
            prev_version.status,
            obj_to_save.status,
        ]:
            logger.debug("Detecting a game finished change.")
            if prev_version.status != "closed" and obj_to_save.status == "closed":
                logger.debug(
                    "Game is newly completed. Adding to count for game and players"
                )
                value_to_add = 1
                if obj_to_save.players.count() > 0:
                    for player in obj_to_save.players.all():
                        notify.send(
                            obj_to_save.gm,
                            recipient=player.user,
                            verb="marked complete game",
                            action_object=obj_to_save,
                        )
            else:
                logger.debug(
                    "Game taken out of completed state. Decreasing count for game and players."
                )
                value_to_add = -1
                if obj_to_save.players.count() > 0:
                    for player in obj_to_save.players.all():
                        notify.send(
                            obj_to_save.gm,
                            recipient=player.user,
                            verb="marked incomplete status",
                            target=obj_to_save,
                        )
            with transaction.atomic():
                obj_to_save.save()
                obj_to_save.gm.gm_games_finished = F("gm_games_finished") + value_to_add
                obj_to_save.gm.save()
                for gamer in obj_to_save.players.all():
                    gamer.games_finished = F("games_finished") + value_to_add
                    gamer.save()
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)


class GamePostingDeleteView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    Deletion view for a game posting.
    """

    model = models.GamePosting
    select_related = ["event", "published_game", "game_system", "published_module"]
    prefetch_related = ["players", "communities"]
    permission_required = "game.can_edit_listing"
    template_name = "games/game_delete.html"
    slug_url_kwarg = "gameid"
    slug_field = "slug"
    context_object_name = "game"

    def get_success_url(self):
        return reverse_lazy("games:game_list")

    def delete(self, request, *args, **kwargs):
        messages.success(
            self.request, _("You have deleted game {}".format(self.get_object().title))
        )
        obj = self.get_object()
        if obj.players.count() > 0:
            for player in obj.players.all():
                notify.send(obj.gm, recipient=player.user, verb="deleted", target=obj)
        return super().delete(request, *args, **kwargs)


class GameSessionList(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.ListView,
):
    """
    List sessions for a particular game.
    """

    model = models.GameSession
    select_related = [
        "game",
        "game__game_system",
        "game__published_game",
        "game__published_module",
        "game__event",
        "occurrence",
        "adventurelog_set",
    ]
    prefetch_related = ["players_expected", "players_missing"]
    permission_required = "game.can_view_listing_details"
    template_name = "games/session_list.html"
    ordering = ["-scheduled_time"]
    context_object_name = "session_list"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def get_queryset(self):
        return self.game.gamesession_set.all().order_by("-scheduled_time")


class GameSessionCreate(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a session.
    """

    model = models.GameSession
    permission_required = "game.can_edit_listing"
    fields = ["game"]
    template_name = "games/session_create.html"
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.method.lower() not in self.http_method_names:
                logging.debug("Disallowed method.")
                return HttpResponseNotAllowed(["POST"])
            game_slug = kwargs.pop("gameid", None)
            self.game = get_object_or_404(models.GamePosting, slug=game_slug)
            if request.user.has_perm(self.permission_required, self.game):
                if self.game.status == "closed":
                    logger.debug("Game is finiahed. Sessions cannot be added.")
                    messages.error(
                        request,
                        _("This game is complete and new sessions cannot be created."),
                    )
                    return HttpResponseRedirect(self.game.get_absolute_url())
                unfinished_sessions = models.GameSession.objects.filter(
                    game=self.game
                ).exclude(status__in=["complete", "cancel"])
                if (
                    models.GameSession.objects.filter(game=self.game)
                    .exclude(status__in=["complete", "cancel"])
                    .count()
                    > 0
                ):
                    logger.debug(
                        "Game has incomplete sessions. Redirecting to probable culprit."
                    )
                    messages.error(
                        request,
                        _(
                            "You cannot create a new session until you have completed the previous one."
                        ),
                    )
                    redirect_session = unfinished_sessions.latest("scheduled_time")
                    return HttpResponseRedirect(redirect_session.get_absolute_url())
            else:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def form_valid(self, form):
        logger.debug("Creating session...")
        self.session = self.game.create_next_session()
        logger.debug("Session created for {}".format(self.session.scheduled_time))
        messages.success(
            self.request, _("Session successfully created. You may edit it as needed.")
        )
        return HttpResponseRedirect(
            reverse_lazy("games:session_edit", kwargs={"session": self.session.slug})
        )


class GameSessionAdHocCreate(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Same as a normal game session create, but instead more permissive in that you can select the time first.
    """

    model = models.GameSession
    permission_required = "game.can_edit_listing"
    template_name = "games/adhoc_session_create.html"
    form_class = forms.AdHocGameSessionForm

    def dispatch(self, request, *args, **kwargs):
        game_slug = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        if request.user.is_authenticated and request.user.has_perm(
            self.permission_required, self.game
        ):
            if self.game.status == "closed":
                logger.debug("Game is finiahed. Sessions cannot be added.")
                messages.error(
                    request,
                    _("This game is complete and new sessions cannot be created."),
                )
                return HttpResponseRedirect(self.game.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["game"] = self.game
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def get_permission_object(self):
        return self.game

    def get_success_url(self):
        self.object.get_absolute_url()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.game = self.game
        self.object.save()
        messages.success(
            self.request, _("You successfully created a new ad hoc session.")
        )
        return HttpResponseRedirect(self.get_success_url())


class GameSessionDetail(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    Show details for a given game session.
    """

    model = models.GameSession
    select_related = [
        "game",
        "game__game_system",
        "game__published_game",
        "game__published_module",
        "game__event",
        "occurrence",
        "adventurelog_set",
    ]
    prefetch_related = ["players_expected", "players_missing"]
    permission_required = "game.can_view_listing_details"
    template_name = "games/session_detail.html"
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["session"].game
        return context


class GameSessionUpdate(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Update a session. (GM only)
    """

    model = models.GameSession
    select_related = ["game"]
    prefetch_related = ["players_expected", "players_missing"]
    permission_required = "game.can_edit_listing"
    template_name = "games/session_edit.html"
    form_class = forms.GameSessionForm
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = models.Player.objects.filter(game=context["session"].game)
        context["game"] = context["session"].game
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["game"] = self.get_object().game
        return kwargs

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()


class GameSessionMove(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    """
    Reschedule a game session.
    """

    model = models.GameSession
    permission_required = "game.can_edit_listing"
    template_name = "games/session_reschedule.html"
    slug_url_kwarg = "session"
    context_object_name = "session"
    slug_field = "slug"
    form_class = forms.GameSessionRescheduleForm  # Fill in later

    def get_success_url(self):
        for player in self.object.players_expected.all():
            notify.send(
                self.object.game.gm,
                recipient=player.gamer.user,
                verb="rescheduled session",
                action_object=self.object,
                target=self.object.game,
            )
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["session"].game
        return context

    def get_permission_object(self):
        return self.get_object().game

    def form_valid(self, form):
        # TODO: Add event conflict checking?
        session = self.get_object()
        session.move(form.cleaned_data["scheduled_time"])
        return HttpResponseRedirect(session.get_absolute_url())


class GameSessionCompleteUnComplete(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Mark a session either complete or incomplete.
    """

    model = models.GameSession
    slug_url_kwarg = "session"
    context_object_name = "session"
    form_class = forms.GameSessionCompleteUncompleteForm
    select_related = ["game"]
    permission_required = "game.can_edit_listing"

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.get_object().game

    def form_invalid(self, form):
        messages.error(
            self.request,
            _("You have submitted invalid data. Were you tampering with the request?"),
        )
        return HttpResponseRedirect(self.get_object().get_absolute_url())

    def form_valid(self, form):
        self.new_version = form.save(commit=False)
        if self.new_version.status not in ["complete", "pending"]:
            return self.form_invalid(form)
        self.new_version.save()
        return HttpResponseRedirect(self.new_version.get_absolute_url())


class GameSessionCancel(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
        Cancel a game session.
        """

    model = models.GameSession
    select_related = [
        "game",
        "game__game_system",
        "game__published_game",
        "game__published_module",
        "game__event",
        "occurrence",
        "adventurelog",
    ]
    prefetch_related = ["players_expected", "players_missing"]
    permission_required = "game.can_edit_listing"
    template_name = "games/session_delete.html"
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"
    fields = ["status"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        obj = self.get_object()
        for player in obj.players_expected.all():
            notify.send(
                self.object.game.gm,
                recipient=player.gamer.user,
                verb="cancelled session",
                action_object=self.object,
                target=self.object.game,
            )
        return self.get_object().get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["session"].game
        return context

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()

    def form_invalid(self, form):
        messages.error(self.request, _("You have submitted invalid data."))
        return HttpResponseRedirect(self.get_object().get_absolute_url())

    def form_valid(self, form):
        session = self.get_object()
        if form.cleaned_data["status"] != "cancel":
            # Invalid use of this view.
            messages.error(
                self.request,
                _(
                    "You cannot call this function to do anything other than cancel a session."
                ),
            )
        else:
            messages.success(
                self.request, _("You have successfully cancelled this session.")
            )
            session.cancel()
        return HttpResponseRedirect(session.get_absolute_url())


class GameSessionUncancel(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Uncancel a session.
    """

    model = models.GameSession
    select_related = [
        "game",
        "game__game_system",
        "game__published_game",
        "game__published_module",
        "game__event",
        "occurrence",
        "adventurelog",
    ]
    prefetch_related = ["players_expected", "players_missing"]
    permission_required = "game.can_edit_listing"
    template_name = "games/session_delete.html"
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"
    fields = ["status"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.get_object().game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["session"].game
        return context

    def form_invalid(self, form):
        messages.error(self.request, _("You have submitted invalid data."))
        return HttpResponseRedirect(self.get_object().get_absolute_url())

    def form_valid(self, form):
        session = self.get_object()
        if form.cleaned_data["status"] != "pending":
            messages.error(
                self.request,
                _(
                    "You may not use this function for anything besides uncanceling a session."
                ),
            )
        else:
            session.uncancel()
            messages.success(
                self.request, _("You have successfully uncanceled this session.")
            )
            for player in session.players_expected.all():
                notify.send(
                    session.game.gm,
                    recipient=player.gamer.user,
                    verb="uncancelled session",
                    action_object=session,
                    target=session.game,
                )
        return HttpResponseRedirect(session.get_absolute_url())


class AdventureLogCreate(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create view for an adventure log.
    """

    model = models.AdventureLog
    permission_required = "game.is_member"
    template_name = "games/log_create.html"
    fields = ["title", "body"]

    def dispatch(self, request, *args, **kwargs):
        session_slug = kwargs.pop("session", None)
        self.session = get_object_or_404(models.GameSession, slug=session_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.session.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session"] = self.session
        context["game"] = self.session.game
        return context

    def form_valid(self, form):
        self.log = form.save(commit=False)
        self.log.session = self.session
        self.log.initial_author = self.request.user.gamerprofile
        self.log.save()
        messages.success(
            self.request, _("You have successfully published a log entry.")
        )
        return HttpResponseRedirect(self.log.session.get_absolute_url())


class AdventureLogUpdate(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Update an existing log.
    """

    model = models.AdventureLog
    permission_required = "game.is_member"
    template_name = "games/log_edit.html"
    slug_url_kwarg = "log"
    slug_field = "slug"
    context_object_name = "log"
    fields = ["title", "body"]

    def get_permission_object(self):
        return self.get_object().session.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["log"].session.game
        return context

    def get_queryset(self):
        return models.AdventureLog.objects.all()

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.last_edited_by = self.request.user.gamerprofile
        obj.save()
        messages.success(
            self.request, _("You have successfully updated this log entry.")
        )
        return HttpResponseRedirect(obj.session.get_absolute_url())


class AdventureLogDelete(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    Delete a log (only gm)
    """

    model = models.AdventureLog
    select_related = ["session", "session__game", "initial_author", "last_edited_by"]
    permission_required = "game.can_edit_listing"
    template_name = "games/log_delete.html"
    slug_url_kwarg = "log"
    slug_field = "slug"
    context_object_name = "log"

    def get_permission_object(self):
        return self.get_object().session.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["log"].session.game
        return context

    def get_success_url(self):
        return self.object.session.get_absolute_url()

    def form_valid(self, form):
        messages.success(
            self.request, _("You have successfully deleted this log entry.")
        )
        return super().form_valid(form)


class CalendarDetail(
    LoginRequiredMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    A calendar view of all of the user's games and whatnot. Links to actual events/sessions.
    """

    model = Calendar
    permission_required = "calendar.can_view"
    prefetch_related = ["event_set"]
    periods = [Month]
    template_name = "games/calendar_detail.html"
    slug_url_kwarg = "gamer"
    context_object_name = "calendar"

    def dispatch(self, request, *args, **kwargs):
        slug_to_use = kwargs["gamer"]
        if request.user.is_authenticated and request.user.username == slug_to_use:
            self.calendar, created = Calendar.objects.get_or_create(
                slug=slug_to_use, defaults={"name": "{}'s calendar".format(slug_to_use)}
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["start_of_month"] = mkfirstOfmonth(timezone.now())
        context["end_of_month"] = mkLastOfMonth(timezone.now())
        context["calendar_slug"] = self.calendar.slug
        return context


class CalendarJSONView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    JSONResponseMixin,
    generic.DetailView,
):
    """
    A JSON response for an ajax request to load api data.
    """

    model = Calendar
    permission_required = "calendar.can_view"
    context_object_name = "calendar"

    def dispatch(self, request, *args, **kwargs):
        self.start = request.GET.copy().get("start")
        print(self.start)
        self.end = request.GET.copy().get("end")
        self.timezone = request.GET.copy().pop("timezone", None)
        self.calendar_slug = request.GET.copy().pop("calendar_slug", None)
        if not self.start:
            print("Create first of month")
            self.start = mkfirstOfmonth(timezone.now()).strftime("%Y-%m-%d")
        else:
            self.start = self.start
        if not self.end:
            print("Create last of month")
            self.end = mkLastOfMonth(timezone.now()).strftime("%Y-%m-%d")
        else:
            self.end = self.end
        if not self.timezone:
            self.timezone = timezone.now().strftime("%z")
        else:
            self.timezone = self.timezone[0]
        if not self.calendar_slug:
            raise Http404
        else:
            self.calendar_slug = self.calendar_slug[0]
        logger.debug("Received '{}' as calendar slug.".format(self.calendar_slug))
        if not self.timezone:
            pass  # We'll fetch user-defined timzone later after we define it.
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        logger.debug(
            "Trying to locate Calendar with slug {}".format(self.calendar_slug)
        )
        return get_object_or_404(self.model, slug=self.calendar_slug)

    def render_to_json_response(self, context, **response_kwargs):
        return super().render_to_json_response(context, safe=False, **response_kwargs)

    def get_queryset(self):
        return Calendar.objects.all()

    def get_data(self, context):
        print(
            "Trying request with start {}, end {}, slug {}, and timezone {}".format(
                self.start, self.end, self.calendar_slug, self.timezone
            )
        )
        return _api_occurrences(self.start, self.end, self.calendar_slug, self.timezone)


def _api_occurrences(start, end, calendar_slug, timezone):

    if not start or not end:
        raise ValueError("Start and end parameters are required")
    # version 2 of full calendar
    # TODO: improve this code with date util package
    if "-" in start:

        def convert(ddatetime):
            if ddatetime:
                ddatetime = ddatetime.split(" ")[0]
                try:
                    return datetime.datetime.strptime(ddatetime, "%Y-%m-%d")
                except ValueError:
                    # try a different date string format first before failing
                    return datetime.datetime.strptime(ddatetime, "%Y-%m-%dT%H:%M:%S")

    else:

        def convert(ddatetime):
            return datetime.datetime.utcfromtimestamp(float(ddatetime))

    start = convert(start)
    end = convert(end)
    current_tz = False
    if timezone and timezone in pytz.common_timezones:
        # make start and end dates aware in given timezone
        current_tz = pytz.timezone(timezone)
        start = current_tz.localize(start)
        end = current_tz.localize(end)
    elif settings.USE_TZ:
        # If USE_TZ is True, make start and end dates aware in UTC timezone
        utc = pytz.UTC
        start = utc.localize(start)
        end = utc.localize(end)

    if calendar_slug:
        # will raise DoesNotExist exception if no match
        calendars = [Calendar.objects.get(slug=calendar_slug)]
    # if no calendar slug is given, get all the calendars
    else:
        calendars = Calendar.objects.all()
    response_data = []
    # Algorithm to get an id for the occurrences in fullcalendar (NOT THE SAME
    # AS IN THE DB) which are always unique.
    # Fullcalendar thinks that all their "events" with the same "event.id" in
    # their system are the same object, because it's not really built around
    # the idea of events (generators)
    # and occurrences (their events).
    # Check the "persisted" boolean value that tells it whether to change the
    # event, using the "event_id" or the occurrence with the specified "id".
    # for more info https://github.com/llazzaro/django-scheduler/pull/169
    i = 1
    if Occurrence.objects.all().count() > 0:
        i = Occurrence.objects.latest("id").id + 1
    event_list = []
    for calendar in calendars:
        # create flat list of events from each calendar
        event_list += calendar.events.filter(start__lte=end).filter(
            Q(end_recurring_period__gte=start) | Q(end_recurring_period__isnull=True)
        )
    for event in event_list:
        occurrences = event.get_occurrences(start, end)
        for occurrence in occurrences:
            occurrence_id = i + occurrence.event.id
            existed = False

            if occurrence.id:
                occurrence_id = occurrence.id
                existed = True

            recur_rule = occurrence.event.rule.name if occurrence.event.rule else None

            if occurrence.event.end_recurring_period:
                recur_period_end = occurrence.event.end_recurring_period
                if current_tz:
                    # make recur_period_end aware in given timezone
                    recur_period_end = recur_period_end.astimezone(current_tz)
                recur_period_end = recur_period_end
            else:
                recur_period_end = None

            event_start = occurrence.start
            event_end = occurrence.end
            if current_tz:
                # make event start and end dates aware in given timezone
                event_start = event_start.astimezone(current_tz)
                event_end = event_end.astimezone(current_tz)
            gevent = models.GameEvent.objects.get(pk=occurrence.event.pk)
            if not occurrence.cancelled:
                response_data.append(
                    {
                        "id": occurrence_id,
                        "title": occurrence.title,
                        "start": event_start,
                        "end": event_end,
                        "url": gevent.get_related_game().get_absolute_url(),
                        "existed": existed,
                        "event_id": occurrence.event.id,
                        "color": occurrence.event.color_event,
                        "description": occurrence.description,
                        "rule": recur_rule,
                        "end_recurring_period": recur_period_end,
                        "creator": str(occurrence.event.creator),
                        "calendar": occurrence.event.calendar.slug,
                        "cancelled": occurrence.cancelled,
                    }
                )
    return response_data


class PlayerLeaveGameView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    For players to leave a game they have already joined.
    """

    model = models.Player
    permission_required = "game.player_leave"
    select_related = ["game"]
    context_object_name = "player"
    slug_url_kwarg = "player"
    slug_field = "slug"
    template_name = "games/player_leave.html"

    def dispatch(self, request, *args, **kwargs):
        game_slug = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.game.get_absolute_url()

    def form_valid(self, form):
        messages.success(
            self.request, _("You have left game {}".format(self.game.title))
        )
        player_left.send(models.Player, player=self.get_object())
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context


class PlayerKickView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    View for a GM to kick a player out of a game.
    """

    model = models.Player
    permission_required = "game.can_edit_listing"
    template_name = "games/player_kick.html"
    context_object_name = "player"
    select_related = ["game"]
    slug_url_kwarg = "player"
    slug_field = "slug"

    def dispatch(self, request, *args, **kwargs):
        game_slug = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.game.get_absolute_url()

    def get_permission_object(self):
        return self.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def delete(self, request, *args, **kwargs):
        logger.debug("Entering delete method...")
        obj = self.get_object()
        messages.success(
            self.request,
            _("You have kicked player {} from game {}".format(obj, self.game.title)),
        )
        objpk = obj.pk
        player_kicked.send(request.user, player=obj)
        with transaction.atomic():
            obj.delete()
        logger.debug("Deleted object with pk {}...".format(objpk))
        return HttpResponseRedirect(self.game.get_absolute_url())


class CharacterCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    Create a character for a game.
    """

    model = models.Character
    fields = ["name", "description", "sheet"]  # TODO
    template_name = "games/character_create.html"
    permission_required = "game.add_character"

    def dispatch(self, request, *args, **kwargs):
        player_slug = kwargs.pop("player", None)
        self.player = get_object_or_404(models.Player, slug=player_slug)
        self.game = self.player.game
        if self.player.game != self.game:
            raise PermissionDenied
        if request.user.is_authenticated:
            if request.user.gamerprofile == self.game.gm:
                messages.error(request, _("GMs cannot create a player character."))
                raise PermissionDenied
            elif request.user.gamerprofile != self.player.gamer:
                messages.error(
                    request, _("You can't create a character for a different player.")
                )
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.player.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        context["player"] = self.player
        return context

    def form_valid(self, form):
        self.character = form.save(commit=False)
        self.character.game = self.game
        self.character.player = self.player
        self.character.save()
        return HttpResponseRedirect(self.character.get_absolute_url())


class CharacterApproveView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.UpdateView,
):
    """
    Approve a character.
    """

    model = models.Character
    slug_url_kwarg = "character"
    slug_field = "slug"
    permission_required = "game.approve_character"
    select_related = ["player", "player__game"]
    fields = ["status"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        messages.error(self.request, _("You submitted invalid data."))
        return HttpResponseRedirect(self.get_object().get_absolute_url())

    def get_permission_object(self):
        return self.get_object().game

    def get_valid_status(self):
        return "approved"

    def get_success_message_text(self, character):
        return _(
            "Character {} has been {}.".format(character.name, self.get_valid_status())
        )

    def form_valid(self, form):
        if form.cleaned_data["status"] != self.get_valid_status():
            return self.form_invalid(form)
        character = self.get_object()
        character.status = form.cleaned_data["status"]
        character.save()
        notify.send(
            self.request.user.gamerprofile,
            recipient=character.player.gamer.user,
            verb="approved your character {}".format(character.name),
            target=character.game,
        )
        messages.success(self.request, self.get_success_message_text(character))
        return HttpResponseRedirect(character.get_absolute_url())


class CharacterRejectView(CharacterApproveView):
    """
    Reject view for a character.
    """

    def get_valid_status(self):
        return "rejected"

    def get_success_message_text(self, character):
        notify.send(
            character.game.gm,
            recipient=character.player.gamer.user,
            verb="Your character {} was not accepted".format(character.name),
            action_object=character,
            target=character.game,
        )
        return _(
            "Character {} has been {}.".format(character.name, self.get_valid_status())
        )


class CharacterMakeInactiveView(CharacterApproveView):
    """
    View for gamer to make a character inactive.
    """

    permission_required = "game.delete_character"

    def get_success_message_text(self, character):
        return _("Character {} has been made inactive.".format(character.name))

    def get_permission_object(self):
        return self.get_object()

    def get_valid_status(self):
        return "inactive"


class CharacterReactivateView(CharacterMakeInactiveView):
    """
    View for gamer to reactivate a character.
    """

    def get_valid_status(self):
        return "pending"

    def get_success_message_text(self, character):
        return _(
            "Character {} has been reactivated and is awaiting approval from the GM.".format(
                character.name
            )
        )


class CharacterListForGame(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.ListView
):
    """
    List of characters associated with game.
    """

    model = models.Character
    select_related = ["player", "player__game"]
    permission_required = "game.is_member"
    template_name = "games/game_character_list.html"
    context_object_name = "character_list"
    game = None

    def dispatch(self, request, *args, **kwargs):
        if not self.game:
            game_slug = kwargs.pop("gameid", None)
            self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def get_queryset(self):
        return models.Character.objects.filter(game=self.game).order_by(
            "player__created", "-created", "name"
        )


class CharacterListForPlayer(CharacterListForGame):
    """
    List of characters for a single player.
    """

    template_name = "games/player_character_list.html"

    def dispatch(self, request, *args, **kwargs):
        player_slug = kwargs.pop("player", None)
        self.player = get_object_or_404(models.Player, slug=player_slug)
        self.game = self.player.game
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["player"] = self.player
        context["game"] = self.game
        return context

    def get_queryset(self):
        return models.Character.objects.filter(player=self.player).order_by("-created")


class CharacterListForGamer(LoginRequiredMixin, SelectRelatedMixin, generic.ListView):
    """
    List of characters for a given gamer. Can only be accessed by the gamer themselves so no permissions required.
    """

    context_object_name = "character_list"
    template_name = "games/my_character_list.html"
    select_related = ["player", "player__game"]

    def get_queryset(self):
        return models.Character.objects.filter(
            player__in=models.Player.objects.filter(
                gamer=self.request.user.gamerprofile
            )
        ).order_by("-player__game__created", "-created")


class CharacterDetail(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.DetailView
):
    """
    Detail view for a chracter.
    """

    model = models.Character
    select_related = ["game", "player", "player__gamer"]
    permission_required = "game.is_member"
    template_name = "games/character_detail.html"
    context_object_name = "character"
    slug_url_kwarg = "character"
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["character"].game
        return context

    def get_permission_object(self):
        return self.get_object().game


class CharacterUpdate(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    """
    Update view for a chracter record.
    """

    model = models.Character
    fields = ["name", "description", "sheet"]
    template_name = "games/character_edit.html"
    context_object_name = "character"
    slug_field = "slug"
    slug_url_kwarg = "character"
    permission_required = "game.edit_character"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["character"].game
        return context


class CharacterDelete(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
    Delete a character.
    """

    model = models.Character
    template_name = "games/character_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "character"
    permission_required = "game.delete_character"
    context_object_name = "character"
    select_related = ["game", "player"]

    def get_success_url(self):
        return self.object.game.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = context["character"].game
        return context


class GameInviteList(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    List of invites for a game (loaded via template tags)
    """

    model = models.GamePosting
    template_name = "games/game_invite_list.html"
    slug_url_kwarg = "slug"
    permission_required = "game.can_edit_listing"
    select_related = ["gm", "published_game", "game_system", "published_module"]
    prefetch_related = ["players", "gamesession_set"]
    context_object_name = "game"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ct"] = ContentType.objects.get_for_model(context["game"])
        return context


class ExportGameDataView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    Serializes game data for export and delivers a JSON file.
    """

    model = models.GamePosting
    slug_url_kwarg = "gameid"
    permission_required = "game.can_edit_listing"
    select_related = ["gm", "published_game", "game_system", "published_module"]
    prefetch_related = [
        "gamesession_set",
        "character_set",
        "players",
        "gamesession_set__players_expected__gamer",
        "gamesession_set__players_missing__gamer",
        "gamesession_set__adventurelog",
        "gamesession_set__adventurelog__initial_author",
        "gamesession_set__adventurelog__last_edited_by",
    ]
    context_object_name = "game"

    def get_data(self):
        serializer = serializers.GameDataSerializer(
            self.get_object(), context={"request": self.request}
        )
        return serializer.data

    def get_queryset(self):
        return models.GamePosting.objects.all()

    def render_to_response(self, context, **response_kwargs):
        response = HttpResponse(
            JSONRenderer().render(self.get_data()), content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="game_{}.json"'.format(
            context["game"].slug
        )
        return response


class ConflictCheckingMixin(object):
    """
    Given a propsed date, and game, check if a session has conflicts.
    """

    game = None
    avail_conflicts = None
    occurrence_conflicts = None

    def get_occurrences_that_overlap(self, gamer_list, start_time, end_time):
        gamer_conflicts = []
        for gamer in gamer_list:
            cal, created = Calendar.objects.get_or_create(
                slug=gamer.username,
                defaults={"name": "{}'s calendar".format(gamer.username)},
            )
            if not created:
                day_period = Day(cal.events.all(), start_time)
                occs = day_period.get_occurrences()
                for occ in occs:
                    gep = models.GameEvent.objects.get(id=occ.event.id)
                    if (
                        not occ.cancelled
                        and occ.start < end_time
                        and occ.end > start_time
                        and gamer not in gamer_conflicts
                        and gep.get_related_game() != self.game
                    ):
                        # Here there be conflict
                        gamer_conflicts.append(gamer)
        return gamer_conflicts

    def avail_compare(self, gamer_list, start, end):
        conflicts = []
        for gamer in gamer_list:
            acal = models.AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
                gamer
            )
            if (
                acal.events.filter(
                    end_recurring_period__isnull=True, rule__isnull=False
                ).count()
                > 0
            ):
                results = acal.check_proposed_time(start, end)
                if results:
                    conflicts.append(gamer)
        return conflicts

    def get_data(self):
        result = {"avail_issues": [], "conflict_issues": []}
        if self.avail_conflicts:
            for conflict in self.avail_conflicts:
                result["avail_issues"].append(str(conflict))
        logger.debug(
            "Found {} availability conflicts".format(len(result["avail_issues"]))
        )
        if self.occurrence_conflicts:
            for conflict in self.occurrence_conflicts:
                result["conflict_issues"].append(str(conflict))
        logger.debug("Found {} game conflicts".format(len(result["conflict_issues"])))
        return result

    def render_to_response(self, context, **response_kwargs):
        response_data = self.get_data()
        response = HttpResponse(
            JSONRenderer().render(response_data), content_type="application/json"
        )
        return response

    def form_invalid(self, form):
        logger.debug(self.request.POST)
        return HttpResponse(
            JSONRenderer().render({"form_errors": form.errors}),
            content_type="application/json",
            status=400,
        )

    def get_game(self):
        if hasattr(self, "game") and self.game:  # Implement
            return self.game
        return None

    def form_valid(self, form):
        self.game = self.get_game()
        start_time = form.cleaned_data["scheduled_time"]
        logger.debug("Received {} for new time".format(start_time))
        end_time = start_time + datetime.timedelta(
            minutes=int(60 * self.game.session_length)
        )
        gamer_list = self.game.players.all()

        self.avail_conflicts = self.avail_compare(gamer_list, start_time, end_time)
        self.occurrence_conflicts = self.get_occurrences_that_overlap(
            gamer_list, start_time, end_time
        )
        return self.render_to_response(self.get_context_data())


class GameSessionRescheduleCheckConflicts(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ConflictCheckingMixin,
    generic.edit.UpdateView,
):
    """
    Provide a JSON reponse of potential conflicts if provided a given date.
    """

    model = models.GameSession
    context_object_name = "session"
    slug_url_kwarg = "session"
    permission_required = "game.can_edit_details"
    # fields = ["scheduled_time"]
    avail_conflicts = None
    occurrence_conflicts = None
    form_class = forms.GameSessionRescheduleForm
    game = None

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        self.game = self.get_object().game
        return self.game

    def form_valid(self, form):
        self.game = self.get_game()
        start_time = form.cleaned_data["scheduled_time"]
        logger.debug("Received {} for new time".format(start_time))
        end_time = start_time + datetime.timedelta(
            minutes=int(60 * self.game.session_length)
        )
        gamer_list = self.game.players.all()

        self.avail_conflicts = self.avail_compare(gamer_list, start_time, end_time)
        self.occurrence_conflicts = self.get_occurrences_that_overlap(
            gamer_list, start_time, end_time
        )
        return self.render_to_response(self.get_context_data())

    def form_invalid(self, form):
        logger.debug(self.request.POST)
        return HttpResponse(
            JSONRenderer().render({"form_errors": form.errors}),
            content_type="application/json",
            status=400,
        )


class AdHocSessionCheckConflicts(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ConflictCheckingMixin,
    generic.CreateView,
):
    model = models.GameSession
    form_class = forms.GameSessionRescheduleForm
    permission_required = "game.can_edit_details"

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in ["post"]:
            return HttpResponseNotAllowed(["POST"])
        if request.user.is_authenticated:
            game_slug = kwargs.pop("game", None)
            self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def form_valid(self, form):
        self.game = self.get_game()
        start_time = form.cleaned_data["scheduled_time"]
        logger.debug("Received {} for new time".format(start_time))
        end_time = start_time + datetime.timedelta(
            minutes=int(60 * self.game.session_length)
        )
        gamer_list = self.game.players.all()

        self.avail_conflicts = self.avail_compare(gamer_list, start_time, end_time)
        self.occurrence_conflicts = self.get_occurrences_that_overlap(
            gamer_list, start_time, end_time
        )
        return self.render_to_response(self.get_context_data())

    def form_invalid(self, form):
        logger.debug(self.request.POST)
        return HttpResponse(
            JSONRenderer().render({"form_errors": form.errors}),
            content_type="application/json",
            status=400,
        )
