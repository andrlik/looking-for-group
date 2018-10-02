from django.views import generic
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from braces.views import SelectRelatedMixin, PrefetchRelatedMixin
from rules.contrib.views import PermissionRequiredMixin
from . import models

# Create your views here.


class GamePostingListView(
    LoginRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    PermissionRequiredMixin,
    generic.ListView,
):
    """
    A generic list view for game postings.
    """

    model = models.GamePosting
    select_related = ["game_system", "published_game", "published_module"]
    prefetch_related = ["players", "communities"]
    permission_required = "games.can_view_listing"
    template_name = "games/game_list.html"

    def get_queryset(self):
        return models.GamePosting.objects.all()


class GamePostingCreateView(LoginRequiredMixin, generic.CreateView):
    """
    Create view for game posting.
    """

    models = models.GamePosting
    fields = [
        "game_type",
        "title",
        "min_players",
        "max_players",
        "adult_themes",
        "content_warning",
        "privacy_level",
        "game_system" "published_game",
        "published_module",
        "game_frequency",
        "start_time",
        "session_length",
        "end_date",
        "game_description",
        "communities",
    ]
    template_name = 'games/game_create.html'
    allowed_communities = None

    def get_success_url(self):
        return self.game_posting.get_absolute_url()

    def get_allowed_communties(self):
        if not self.allowed_communities:
            self.allowed_communities = self.request.user.gamerprofile.communties.all()
        return self.allowed_communities

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowed_communities'] = self.get_allowed_communties()
        return context

    def form_valid(self, form):
        self.game_posting = form.save(commit=False)
        if self.game_posting.commmunities:
            for comm in self.game_posting.communities:
                if comm not in self.get_allowed_communties():
                    messages.error(self.request, _("You do not have permission to post games into community {}".format(comm.name)))
                    return self.form_invalid(form)
        self.game_posting.save()
        return HttpResponseRedirect(self.get_success_url())


class GamePostingDetailView(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.DetailView):
    '''
    Detail view for a game posting.
    '''

    model = models.GamePosting
    select_related = ['event', 'published_game', 'game_system', 'published_module', 'gamesession_set', 'gamesession_set__adventurelog']
    prefetch_related = ['players', 'communities']
    permission_required = 'games.can_view_listing'
    template_name = 'games/game_detail.html'

    def get_queryset(self):
        return models.GamePosting.objects.all()


class GamePostingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView):
    '''
    Update view for a game posting.
    '''
    model = models.GamePosting
    permission_required = 'games.can_edit_listing'
    template_name = 'games/game_detail.html'
    fields = [
        "game_type",
        "title",
        "min_players",
        "max_players",
        "adult_themes",
        "content_warning",
        "privacy_level",
        "game_system" "published_game",
        "published_module",
        "game_frequency",
        "start_time",
        "session_length",
        "end_date",
        "game_description",
        "communities",
    ]
    allowed_communities = None

    def get_success_url(self):
        return self.get_object().get_absolute_url()

    def get_allowed_communities(self):
        if not self.allowed_communities:
            self.allowed_communities = self.request.user.gamerprofile.communities.all()
        return self.allowed_communities

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowed_communities'] = self.get_allowed_communities()
        return context

    def form_valid(self, form):
        if form.instance.communities:
            for comm in form.instance.communities:
                if comm not in self.get_allowed_communities():
                    messages.error(self.request, _("You do not have permission to post this game in community {}.".format(comm.name)))
                    return self.form_invalid(form)
        return super().form_valid(form)


class GamePostingDeleteView(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.edit.DeleteView):
    '''
    Deletion view for a game posting.
    '''
    model = models.GamePosting
    select_related = ['event', 'gamesession_set', 'gamesession_set__adventurelog', 'published_game', 'game_system', 'published_module']
    prefetch_related = ['players', 'communities', 'players__character_set']
    permission_required = 'games.can_edit_listing'
    template_name = 'games/game_delete.html'


class GameSessionList(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.ListView):
    '''
    List sessions for a particular game.
    '''
    model = models.GameSession
    select_related = ['game', 'game__game_system', 'game__published_game', 'game__published_module', 'game__event', 'occurrence', 'adventurelog_set']
    prefetch_related = ['players_expected', 'players_missing']
    permission_required = 'games.is_member'
    template_name = 'games/session_list.html'
    ordering = ['-scheduled_time']
    context_object_name = 'sessions'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop('game', None)
        self.game = get_object_or_404(models.GamePosting, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_queryset(self):
        return self.game.gamesession_set.all()


class GameSessionCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    '''
    Create a session.
    '''
    permission_required = 'games.can_edit_listing'
    fields = ['game']
    template_name = 'games/session_create.html'

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop('game', None)
        self.game = get_object_or_404(models.GameSession, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['game'] = self.game
        context['occurrence'] = self.game.get_next_scheduled_occurrence()
        return context

    def get_permission_object(self):
        return self.game

    def form_valid(self, form):
        self.session = self.game.generate_session_from_occurence(self.game.get_next_scheduled_occurrence())
        return HttpResponseRedirect(self.session.get_absolute_url())


class GameSessionDetail(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.DetailView):
    '''
    Show details for a given game session.
    '''
    model = models.GameSession
    select_related = ['game', 'game__game_system', 'game__published_game', 'game__published_module', 'game__event', 'occurrence', 'adventurelog_set']
    prefetch_related = ['players_expected', 'players_missing']
    permission_required = 'games.is_member'
    template_name = 'games/session_detail.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session'

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()


class GameSessionUpdate(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.edit.UpdateView):
    '''
    Update a session. (GM only)
    '''
    model = models.GameSession
    select_related = ['game']
    prefetch_related = ['players_expected', 'players_missing']
    permission_required = 'games.can_edit_listing'
    template_name = 'games/session_edit.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['players'] = models.Player.objects.filter(game=context['session'].game)
        return context

    def get_permission_object(self):
        return self.get_object().game

    def get_queryset(self):
        return models.GameSession.objects.all()


class GameSessionDelete(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.edit.DeleteView):
        '''
        Delete a game session.
        '''

        model = models.GameSession
        select_related = ['game', 'game__game_system', 'game__published_game', 'game__published_module', 'game__event', 'occurrence', 'adventurelog_set']
        prefetch_related = ['players_expected', 'players_missing']
        permission_required = 'games.can_edit_listing'
        template_name = 'games/session_delete.html'
        context_object_name = 'session'
        pk_url_kwarg = 'session'

        def get_permission_object(self):
            return self.get_object().game

        def get_queryset(self):
            return models.GameSession.objects.all()


class AdventureLogList(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.ListView):
    '''
    List view for adventure logs.
    '''
    model = models.AdventureLog
    select_related = ['session', 'session__game']
    prefetch_related = ['session__players_expected', 'session__players_missing']
    paginate_by = 10
    context_object_name = 'logs'
    template = 'games/log_list.html'
    permission_required = 'games.is_member'
    ordering = ['-session__scheduled_time', '-created']

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop('game', None)
        self.game = get_object_or_404(models.GamePosting, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.game

    def get_queryset(self):
        return models.AdventureLog.objects.filter(session__in=self.game.gamesession_set.all())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['game'] = self.game
        return context


class AdventureLogDetail(LoginRequiredMixin, SelectRelatedMixin, PrefetchRelatedMixin, PermissionRequiredMixin, generic.DetailView):
    '''
    Detail view for an adventure log post.
    '''

    model = models.AdventureLog
    select_related = ['session', 'session__game']
    prefetch_related = ['session__players_expected', 'session__players_missing']
    permission_required = 'games.is_member'
    context_object_name = 'log'
    pk_url_kwarg = 'log'
    template = 'games/log_detail.html'

    def get_permission_object(self):
        return self.get_object().session.game

    def get_queryset(self):
        return models.AdventureLog.objects.all()


class AdventureLogCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    '''
    Create view for an adventure log.
    '''

    model = models.AdventureLog
    permission_required = 'games.is_member'
    template = 'games/log_create.html'
    fields = ['title', 'body']

    def dispatch(self, request, *args, **kwargs):
        session_pk = kwargs.pop('session', None)
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


class AdventureLogUpdate(LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.edit.UpdateView):
    '''
    Update an existing log.
    '''
    model = models.AdventureLog
    permission_required = 'games.is_member'
    template_name = 'games/log_edit.html'
    pk_url_kwarg = 'log'
    fields = ['title', 'body']

    def get_permission_object(self):
        return self.get_object().session.game

    def get_queryset(self):
        return models.AdventureLog.objects.all()

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.last_edited_by = self.request.user.gamerprofile
        obj.save()
        return HttpResponseRedirect(obj.get_absolute_url())


class AdventureLogDelete(LoginRequiredMixin, SelectRelatedMixin, PermissionRequiredMixin, generic.edit.DeleteView):
    '''
    Delete a log (only gm)
    '''
    model = models.AdventureLog
    select_related = ['session', 'session__game', 'initial_author', 'last_edited_by']
    permission_required = 'games.can_edit_listing'
    template_name = 'games/log_delete.html'
    pk_url_kwarg = 'log'
    context_object_name = 'log'

    def get_permission_object(self):
        return self.get_object().session.game
