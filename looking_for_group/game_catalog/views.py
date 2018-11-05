from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from .models import GameEdition, GamePublisher, GameSystem, PublishedGame, PublishedModule, SourceBook

# Create your views here.
# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.


class GamePublisherListView(PrefetchRelatedMixin, generic.ListView):
    """
    List view of game publishers. We prefetch so we can list number of games, modules, etc.
    """

    model = GamePublisher
    prefetch_related = ["gamesystem_set", "gameedition_set", "publishedmodule_set"]
    template_name = "catalog/pub_list.html"
    ordering = ["name"]
    paginate_by = 30
    paginate_orphans = 4


class GamePublisherDetailView(PrefetchRelatedMixin, generic.DetailView):
    model = GamePublisher
    prefetch_related = ["gamesystem_set", "gameedition_set", "publishedmodule_set"]
    pk_url_kwarg = "publisher"
    context_object_name = "publisher"
    template_name = "catalog/pub_detail.html"


class GamePublisherUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update a game publisher view.
    """

    model = GamePublisher
    pk_url_kwarg = "publisher"
    context_object_name = "publisher"
    template_name = "catalog/pub_edit.html"
    fields = ["name", "logo", "url"]
    permission_required = "catalog.can_edit"

    def get_success_url(self):
        return self.object.get_absolute_url()


class GamePublisherCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a new game publisher.
    """

    model = GamePublisher
    fields = ["name", "logo", "url"]
    permission_required = "catalog.can_edit"
    template_name = "catalog/pub_create.html"

    def get_permission_object(self):
        return self.model

    def get_success_url(self):
        self.object.get_absolute_url()


class GamePublisherDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete a game publisher.
    """

    model = GamePublisher
    permission_required = "catalog.can_edit"
    prefetch_related = ["gameedition_set", "gamesystem_set", "publishedmodule_set"]
    template_name = "catalog/pub_delete.html"
    context_object_name = "publisher"
    pk_url_kwarg = "publisher"

    def get_success_url(self):
        return reverse_lazy("game_catalog:pub-list")


class GameSystemCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a game system.
    """

    model = GameSystem
    permission_required = "catalog.can_edit"
    template_name = "catalog/system_create.html"
    fields = [
        "name",
        "image",
        "system_url",
        "description",
        "original_publisher",
        "ogl_license",
        "publication_date",
        "tags",
    ]

    def get_permission_object(self):
        return self.model

    def get_success_url(self):
        return self.object.get_absolute_url()


class GameSystemListView(SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView):
    model = GameSystem
    select_related = ["original_publisher"]
    prefetch_related = ["game_editions"]
    template_name = "catalog/system_list.html"
    ordering = ["name"]
    paginate_by = 30
    paginate_orphans = 4


class GameSystemDetailView(
    SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView
):
    model = GameSystem
    select_related = ["original_publisher"]
    prefetch_related = ["game_editions"]
    pk_url_kwarg = "system"
    context_object_name = "system"
    template_name = "catalog/system_detail.html"


class GameSystemUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for game system.
    """

    model = GameSystem
    context_object_name = "system"
    pk_url_kwarg = "system"
    permission_required = "catalog.can_edit"
    fields = [
        "name",
        "image",
        "system_url",
        "description",
        "original_publisher",
        "ogl_license",
        "publication_date",
        "tags",
    ]
    template_name = "catalog/system_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class GameSystemDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for game system.
    """

    model = GameSystem
    context_object_name = "system"
    select_related = ["original_publisher"]
    prefetch_related = ["game_editions", "gameposting_set", "gamerprofile_set"]
    pk_url_kwarg = "system"
    permission_required = "catalog.can_edit"
    template_name = "catalog/system_delete.html"
    success_url = reverse_lazy("game_catalog:system-list")


class PublishedGameCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a published game.
    """

    model = PublishedGame
    permission_required = "catalog.can_edit"
    template_name = "catalog/game_create.html"
    fields = ["title", "image", "url", "description", "tags"]

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_permission_object(self):
        return self.model


class PublishedGameListView(PrefetchRelatedMixin, generic.ListView):
    model = PublishedGame
    prefetch_related = ["editions"]
    template_name = "catalog/game_list.html"
    ordering = ["title", "-publication_date"]
    paginate_by = 30
    paginate_orphans = 4


class PublishedGameUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a game
    """

    model = PublishedGame
    permission_required = "catalog.can_edit"
    fields = ["title", "image", "url", "description", "publication_date", "tags"]
    pk_url_kwarg = "game"
    context_object_name = "game"
    template_name = "catalog/game_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class PublishedGameDetailView(PrefetchRelatedMixin, generic.DetailView):
    model = PublishedGame
    prefetch_related = ["editions"]
    pk_url_kwarg = "game"
    context_object_name = "game"
    template_name = "catalog/game_detail.html"


class PublishedGameDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for published game.
    """

    model = PublishedGame
    permission_required = "catalog.can_edit"
    context_object_name = "game"
    prefetch_related = ["editions"]
    pk_url_kwarg = "game"
    template_name = "catalog/game_delete.html"
    success_url = reverse_lazy("game_catalog:game-list")


class EditionCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create view for a new edition.
    """

    model = GameEdition
    permission_required = "catalog.can_edit"
    fields = [
        "name",
        "game_system",
        "image",
        "url",
        "publisher",
        "release_date",
        "description",
        "url",
        "tags",
    ]
    template_name = "catalog/edition_create.html"

    def get_permission_object(self):
        return self.model

    def dispatch(self, request, *args, **kwargs):
        game_pk = kwargs.pop("game", None)
        self.game = get_object_or_404(PublishedGame, pk=game_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        return context

    def form_valid(self, form):
        edition = form.save(commit=False)
        edition.game = self.game
        edition.save()
        return HttpResponseRedirect(edition.get_absolute_url())


class EditionUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update view for a game edition.
    """

    model = GameEdition
    permission_required = "catalog.can_edit"
    fields = [
        "name",
        "game_system",
        "image",
        "url",
        "publisher",
        "release_date",
        "description",
        "url",
        "tags",
    ]
    context_object_name = "edition"
    slug_url_kwarg = "edition"
    template_name = "catalog/edition_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class EditionDetailView(SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView):
    model = GameEdition
    select_related = ["game_system", "publisher", "game"]
    prefetch_related = ["publishedmodule_set", "sourcebooks"]
    slug_url_kwarg = "edition"
    slug_field = "slug"
    context_object_name = "edition"
    template_name = "catalog/edition_detail.html"


class EditionDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a game edition.
    """

    model = GameEdition
    slug_url_kwarg = "edition"
    select_related = ["publisher", "game_system", "game"]
    prefetch_related = ["publishedmodule_set", "sourcebooks", "gameposting_set"]
    context_object_name = "edition"
    permission_required = "catalog.can_edit"
    template_name = "catalog/edition_delete.html"

    def delete(self, request, *args, **kwargs):
        self.game = self.get_object().game
        self.success_url = self.game.get_absolute_url()
        return super().delete(request, *args, **kwargs)


class SourceBookCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create view for a new sourcebook.
    """

    model = SourceBook
    fields = ["title", "image", "corebook", "release_date", "isbn", "tags"]
    permission_required = "catalog.can_edit"
    template_name = "catalog/sourcebook_create.html"

    def dispatch(self, request, *args, **kwargs):
        edition_slug = kwargs.pop("edition", None)
        self.edition = get_object_or_404(GameEdition, slug=edition_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.model

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edition"] = self.edition
        return context

    def form_valid(self, form):
        self.book = form.save(commit=False)
        self.book.edition = self.edition
        self.book.save()
        return HttpResponseRedirect(self.book.get_absolute_url())


class SourceBookDetailView(SelectRelatedMixin, generic.DetailView):
    model = SourceBook
    select_related = ["edition", "edition__game"]
    context_object_name = "book"
    template_name = "catalog/sourcebook_detail.html"
    slug_url_kwarg = "book"
    slug_field = "slug"


class SourceBookUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Edit view for a source book.
    """

    model = SourceBook
    fields = ["title", "image", "corebook", "release_date", "isbn", "tags"]
    permission_required = "catalog.can_edit"
    context_object_name = "book"
    slug_url_kwarg = "book"
    template_name = "catalog/sourcebook_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class SourceBookDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a sourcebook.
    """

    model = SourceBook
    permission_required = "catalog.can_edit"
    context_object_name = "book"
    slug_url_kwarg = "book"
    template_name = "catalog/sourcebook_delete.html"
    select_related = [
        "edition",
        "edition__game",
        "edition__publisher",
        "edition__game_system",
    ]

    def delete(self, request, *args, **kwargs):
        self.success_url = self.get_object().edition.get_absolute_url()
        return super().delete(request, *args, **kwargs)


class PublishedModuleCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView
):
    """
    Create a published module.
    """

    model = PublishedModule
    permission_required = "catalog.can_edit"
    template_name = "catalog/module_create.html"
    fields = ["title", "image", "url", "publisher", "publication_date", "isbn", "tags"]

    def get_permission_object(self):
        return self.model

    def dispatch(self, request, *args, **kwargs):
        edition_slug = kwargs.pop("edition", None)
        self.edition = get_object_or_404(GameEdition, slug=edition_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edition"] = self.edition
        return context

    def form_valid(self, form):
        self.module = form.save(commit=False)
        self.module.parent_game_edition = self.edition
        self.module.save()
        return HttpResponseRedirect(self.module.get_absolute_url())


class PublishedModuleListView(SelectRelatedMixin, generic.ListView):
    model = PublishedModule
    select_related = [
        "parent_game_edition",
        "publisher",
        "parent_game_edition__game_system",
    ]
    template_name = "catalog/module_list.html"
    ordering = [
        "title",
        "parent_game_edition__game__title",
        "parent_game_edition__name",
    ]
    paginate_by = 30
    paginate_orphans = 4


class PublishedModuleUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, generic.edit.UpdateView
):
    """
    Update a published module.
    """

    model = PublishedModule
    context_object_name = "module"
    pk_url_kwarg = "module"
    fields = ["title", "image", "url", "publisher", "publication_date", "isbn", "tags"]
    permission_required = "catalog.can_edit"
    template_name = "catalog/module_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()


class PublishedModuleDetailView(SelectRelatedMixin, generic.DetailView):
    model = PublishedModule
    select_related = [
        "parent_game_edition",
        "parent_game_edition__game_system",
        "publisher",
    ]
    pk_url_kwarg = "module"
    context_object_name = "module"
    template_name = "catalog/module_detail.html"


class PublishedModuleDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SelectRelatedMixin,
    PrefetchRelatedMixin,
    generic.edit.DeleteView,
):
    """
    Delete view for a module.
    """

    model = PublishedModule
    context_object_name = "module"
    pk_url_kwarg = "module"
    permission_required = "catalog.can_edit"
    template_name = "catalog/module_delete.html"
    select_related = ["parent_game_edition", "publisher"]
    prefetch_related = ["gameposting_set"]

    def delete(self, request, *args, **kwargs):
        self.success_url = self.get_object().parent_game_edition.get_absolute_url()
        return super().delete(request, *args, **kwargs)
