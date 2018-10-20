from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query_utils import Q
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin
from schedule.models import Calendar
from schedule.periods import Month
from schedule.views import CalendarByPeriodsView, _api_occurrences

from . import forms, models
from .mixins import JSONResponseMixin

# Create your views here.


class GamePostingListView(
    LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView
):
    """
    A generic list view for game postings.
    """

    model = models.GamePosting
    select_related = ["game_system", "published_game", "published_module"]
    prefetch_related = ["players", "communities"]
    template_name = "games/game_list.html"
    context_object_name = "game_list"
    paginate_by = 15
    paginate_orphans = 3

    def get_queryset(self):
        gamer = self.request.user.gamerprofile
        friends = gamer.friends.all()
        communities = [f.id for f in gamer.communities.all()]
        game_player_ids = [
            obj.game.id
            for obj in models.Player.objects.filter(gamer=gamer).select_related("game")
        ]
        q_gm = Q(gm=gamer)
        q_gm_is_friend = Q(gm__in=friends) & Q(privacy_level="community")
        q_isplayer = Q(id__in=game_player_ids)
        q_community = Q(communities__id__in=communities) & Q(privacy_level="community")
        q_public = Q(privacy_level="public")
        return models.GamePosting.objects.exclude(
            status__in=["cancel", "closed"]
        ).filter(q_gm | q_public | q_gm_is_friend | q_isplayer | q_community)


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
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["gamer"] = self.request.user.gamerprofile
        return kwargs

    def form_valid(self, form):
        self.game_posting = form.save(commit=False)
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
        self.game_posting.save()
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

    def form_valid(self, form):
        application = form.save(commit=False)
        if "submit_app" in self.request.POST.keys():
            application.status = 'pending'
        application.gamer = self.request.user.gamerprofile
        application.game = self.game
        application.save()
        return HttpResponseRedirect(application.get_absolute_url())


class GamePostingApplicationDetailView(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.DetailView
):
    """
    View for an application detail.
    """

    model = models.GamePostingApplication
    context_object_name = "application"
    select_related = ['game', 'gamer']
    slug_url_kwarg = "application"
    slug_field = "slug"
    permission_required = "game.view_application"
    template_name = "games/game_apply_detail.html"


class GamePostingApplicationUpdateView(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a game application.
    """

    model = models.GamePostingApplication
    slug_url_kwarg = "application"
    select_related = ["game"]
    slug_field = "slug"
    permission_required = "game.edit_application"
    context_object_name = 'application'
    template_name = "games/game_apply_update.html"
    fields = ["message"]

    def dispatch(self, request, *args, **kwargs):
        self.application = self.get_object()
        if request.user.is_authenticated and request.user.gamerprofile == self.application.gamer and self.application.status not in ['new', 'pending']:
            messages.error(request, _("This application has been processed and can no longer be edited."))
            return HttpResponseRedirect(self.application.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_object().get_absolute_url()

    def form_valid(self, form):
        if "submit_app" in self.request.POST.keys():
            form.instance.status = 'pending'
        return super().form_valid(form)


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
    slug_url_kwarg = 'application'

    def get_success_url(self):
        return self.get_object().game.get_absolute_url()


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
    context_object_name = 'game'

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
        return context


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
    select_related = [
        "event",
        "published_game",
        "game_system",
        "published_module",
    ]
    prefetch_related = ["players", "communities", "players__character_set"]
    permission_required = "game.can_edit_listing"
    template_name = "games/game_delete.html"
    slug_url_kwarg = "gameid"
    slug_field = "slug"
    context_object_name = 'game'

    def get_success_url(self):
        return reverse_lazy('games:game_list')

    def form_valid(self, form):
        messages.success(self.request, _("You have deleted game {}".format(self.get_object().title)))
        return super().form_valid(form)


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
    permission_required = "games.is_member"
    template_name = "games/session_list.html"
    ordering = ["-scheduled_time"]
    context_object_name = "sessions"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_queryset(self):
        return self.game.gamesession_set.all()


class GameSessionCreate(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a session.
    """

    permission_required = "games.can_edit_listing"
    fields = ["game"]
    template_name = "games/session_create.html"
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            return HttpResponseNotAllowed(["POST"])
        game_pk = kwargs.pop("game", None)
        self.game = get_object_or_404(models.GameSession, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        context["occurrence"] = self.game.get_next_scheduled_occurrence()
        return context

    def get_permission_object(self):
        return self.game

    def form_valid(self, form):
        self.session = self.game.generate_session_from_occurence(
            self.game.get_next_scheduled_occurrence()
        )
        return HttpResponseRedirect(self.session.get_absolute_url())


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
    permission_required = "games.is_member"
    template_name = "games/session_detail.html"
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()


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
    permission_required = "games.can_edit_listing"
    template_name = "games/session_edit.html"
    form_class = forms.GameSessionForm
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = models.Player.objects.filter(game=context["session"].game)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["game"] = self.game
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
    permission_required = "game.can_schedule"
    template_name = "games/session_reschedule.html"
    slug_url_kwarg = "session"
    slug_field = "slug"
    form_class = forms.GameSessionRescheduleForm  # Fill in later

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        # TODO: Add event conflict checking?
        session = self.get_object()
        session = session.move(form.cleaned_data["scheduled_time"])
        return HttpResponseRedirect(self.get_success_url())


class GameSessionDelete(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.edit.DeleteView,
):
    """
        Delete a game session.
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
    permission_required = "games.can_edit_listing"
    template_name = "games/session_delete.html"
    context_object_name = "session"
    slug_url_kwarg = "session"
    slug_field = "slug"

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()


class AdventureLogList(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.ListView,
):
    """
    List view for adventure logs.
    """

    model = models.AdventureLog
    select_related = ["session", "session__game"]
    prefetch_related = ["session__players_expected", "session__players_missing"]
    paginate_by = 10
    context_object_name = "logs"
    template = "games/log_list.html"
    permission_required = "games.is_member"
    ordering = ["-session__scheduled_time", "-created"]

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop("gameid", None)
        self.game = get_object_or_404(models.GamePosting, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_queryset(self):
        return models.AdventureLog.objects.filter(
            session__in=self.game.gamesession_set.all()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context


class AdventureLogDetail(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.DetailView,
):
    """
    Detail view for an adventure log post.
    """

    model = models.AdventureLog
    select_related = ["session", "session__game"]
    prefetch_related = ["session__players_expected", "session__players_missing"]
    permission_required = "games.is_member"
    context_object_name = "log"
    slug_url_kwarg = "log"
    slug_field = "slug"
    template = "games/log_detail.html"

    def get_permission_object(self):
        return self.get_object().session.game

    def get_queryset(self):
        return models.AdventureLog.objects.all()


class AdventureLogCreate(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create view for an adventure log.
    """

    model = models.AdventureLog
    permission_required = "games.is_member"
    template = "games/log_create.html"
    fields = ["title", "body"]

    def dispatch(self, request, *args, **kwargs):
        session_pk = kwargs.pop("session", None)
        self.session = get_object_or_404(models.GameSession, pk=session_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.session.game

    def form_valid(self, form):
        self.log = form.save(commit=False)
        self.log.session = self.session
        self.log.initial_author = self.request.user.gamerprofile
        self.log.save()
        return HttpResponseRedirect(self.log.get_absolute_url())


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
    permission_required = "games.is_member"
    template_name = "games/log_edit.html"
    slug_url_kwarg = "log"
    slug_field = "slug"
    fields = ["title", "body"]

    def get_permission_object(self):
        return self.get_object().session.game

    def get_queryset(self):
        return models.AdventureLog.objects.all()

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.last_edited_by = self.request.user.gamerprofile
        obj.save()
        return HttpResponseRedirect(obj.get_absolute_url())


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
    permission_required = "games.can_edit_listing"
    template_name = "games/log_delete.html"
    slug_url_kwarg = "log"
    slug_field = "slug"
    context_object_name = "log"

    def get_permission_object(self):
        return self.get_object().session.game


class CalendarDetail(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    CalendarByPeriodsView,
):
    """
    A calendar view of all of the user's games and whatnot. Links to actual events/sessions.
    """

    model = Calendar
    permission_required = "calendar.can_view"
    select_related = ["event_set"]
    prefetch_related = ["event_set__gameposting_set"]
    periods = [Month]
    template_name = "games/calendar_detail.html"
    slug_url_kwarg = "gamer"


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
    select_related = ["events"]
    context_object_name = "calendar"
    slug_url_kwarg = "calendar"

    def dispatch(self, request, *args, **kwargs):
        self.start = request.GET.get("start")
        self.end = request.GET.get("end")
        self.timezone = request.GET.pop("timezone", None)
        if not self.timezone:
            pass  # We'll fetch user-defined timzone later after we define it.
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Calendar.objects.all()

    def get_data(self, context):
        return _api_occurrences(
            self.start, self.end, context["calendar"].slug, self.timezone
        )


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
        game_slug = kwargs.pop("game", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.game.get_absolute_url()

    def form_valid(self, form):
        messages.success(
            self.request, _("You have left game {}".format(self.game.title))
        )
        return super().form_valid(form)


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
        game_slug = kwargs.pop("game", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.game.get_absolute_url()

    def form_valid(self, form):
        messages.success(
            self.request,
            _(
                "You have kicked player {} from game {}".format(
                    self.get_object(), self.game.title
                )
            ),
        )
        return super().form_valid(form)


class CharacterCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    """
    Create a character for a game.
    """

    model = models.Character
    fields = ["name", "sheet"]  # TODO
    template_name = "games/character_create.html"
    permission_required = "game.can_add_character"

    def dispatch(self, request, *args, **kwargs):
        game_slug = kwargs.pop("game", None)
        player_slug = kwargs.pop("player", None)
        self.game = get_object_or_404(models.GamePosting, slug=game_slug)
        self.player = get_object_or_404(models.Player, slug=player_slug)
        if self.player.game != self.game:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.player

    def form_valid(self, form):
        self.character = form.save(commit=False)
        self.character.game = self.game
        self.character.player = self.player
        self.character.save()
        return HttpResponseRedirect(self.character.get_aboslute_url)


class CharacterDetail(
    LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.DetailView
):
    """
    Detail view for a chracter.
    """

    model = models.Character
    select_related = ["game", "player", "player__gamer"]
    permission_required = "game.view_character"
    template_name = "games/character_detail.html"
    context_object_name = "character"
    slug_url_kwarg = "character"
    slug_field = "slug"


class CharacterUpdate(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    """
    Update view for a chracter record.
    """

    model = models.Character
    fields = ["name", "sheet"]
    template_name = "games/character_update.html"
    slug_field = "slug"
    slug_url_kwarg = "character"
    permission_required = "game.edit_character"


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
    permission_required = "game.edit_character"
    select_related = ["game", "player"]
