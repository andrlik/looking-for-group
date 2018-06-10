from django.views import generic
from braces.views import SelectRelatedMixin, PrefetchRelatedMixin
from .models import GamePublisher, GameSystem, PublishedGame, PublishedModule

# Create your views here.
# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.


class GamePublisherListView(PrefetchRelatedMixin, generic.ListView):
    """
    List view of game publishers. We prefetch so we can list number of games, modules, etc.
    """

    model = GamePublisher
    prefetch_related = ["gamesystem_set", "publishedgame_set", "publishedmodule_set"]
    template_name = 'catalog/publisher_list.html'

    def get_queryset(self):
        return super().get_queryset().order_by("name")


class GamePublisherDetailView(PrefetchRelatedMixin, generic.DetailView):
    model = GamePublisher
    prefetch_related = ["gamesystem_set", "publishedgame_set", "publishedmodule_set"]
    pk_url_kwarg = "publisher"
    context_object_name = 'publisher'
    template_name = 'catalog/publisher_detail.html'


class GameSystemListView(SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView):
    model = GameSystem
    select_related = ["original_publisher"]
    prefetch_related = ["publishedgame_set", "publishedmodule_set"]
    template_name = 'catalog/system_list.html'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .order_by("original_publisher__name", "name", "-created")
        )


class GameSystemDetailView(
    SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView
):
    model = GameSystem
    select_related = ["original_publisher"]
    prefetch_related = ["publishedgame_set", "publishedmodule_set"]
    pk_url_kwarg = "system"
    context_object_name = 'system'
    template_name = 'catalog/system_detail.html'


class PublishedGameListView(SelectRelatedMixin, PrefetchRelatedMixin, generic.ListView):
    model = PublishedGame
    select_related = ["publisher", "game_system"]
    prefetch_related = ["publishedmodule_set"]
    template_name = 'catalog/game_list.html'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .order_by("publisher__name", "game_system__name", "title", "-created")
        )


class PublishedGameDetailView(
    SelectRelatedMixin, PrefetchRelatedMixin, generic.DetailView
):
    model = PublishedGame
    select_related = ["publisher", "game_system"]
    prefetch_related = ["publishedmodule_set"]
    pk_url_kwarg = "game"
    context_object_name = "game"
    template_name = 'catalog/game_detail.html'


class PublishedModuleListView(SelectRelatedMixin, generic.ListView):
    model = PublishedModule
    select_related = ["publishedgame", "publisher", "publishedgame__game_system"]
    template_name = 'catalog/module_list.html'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .order_by("publishedgame__title", "publisher__name", "title", "-created")
        )


class PublishedModuleDetailView(SelectRelatedMixin, generic.DetailView):
    model = PublishedModule
    select_related = ["publishedgame", "publishedgame__game_system", "publisher"]
    pk_url_kwarg = "module"
    context_object_name = "module"
    template_name = 'catalog/module_detail.html'
