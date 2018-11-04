from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.views import generic

from .models import (
    GamePublisher,
    GameSystem,
    PublishedGame,
    PublishedModule,
    GameEdition,
    SourceBook,
)

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


class PublishedGameListView(PrefetchRelatedMixin, generic.ListView):
    model = PublishedGame
    prefetch_related = ["editions"]
    template_name = "catalog/game_list.html"
    ordering = ["title", "-publication_date"]
    paginate_by = 30
    paginate_orphans = 4


class PublishedGameDetailView(PrefetchRelatedMixin, generic.DetailView):
    model = PublishedGame
    prefetch_related = ["editions"]
    pk_url_kwarg = "game"
    context_object_name = "game"
    template_name = "catalog/game_detail.html"


class EditionDetailView(SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView):
    model = GameEdition
    select_related = ["game_system", "publisher", "game"]
    prefetch_related = ["publishedmodule_set", "sourcebooks"]
    slug_url_kwarg = "edition"
    slug_field = "slug"
    context_object_name = "edition"
    template_name = "catalog/edition_detail.html"


class SourceBookDetailView(SelectRelatedMixin, generic.DetailView):
    model = SourceBook
    select_related = ["edition", "edition__game"]
    context_object_name = "book"
    template_name = "catalog/sourcebook_detail.html"
    slug_url_kwarg = "book"
    slug_field = "slug"


class PublishedModuleListView(SelectRelatedMixin, generic.ListView):
    model = PublishedModule
    select_related = ["parent_game_edition", "publisher", "parent_game_edition__game_system"]
    template_name = "catalog/module_list.html"
    ordering = ["title", "parent_game_edition__game__title", "parent_game_edition__name"]
    paginate_by = 30
    paginate_orphans = 4


class PublishedModuleDetailView(SelectRelatedMixin, generic.DetailView):
    model = PublishedModule
    select_related = ["parent_game_edition", "parent_game_edition__game_system", "publisher"]
    pk_url_kwarg = "module"
    context_object_name = "module"
    template_name = "catalog/module_detail.html"
