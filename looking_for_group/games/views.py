from django.views import generic
from django.http import HttpResponseRedirect
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
