from rest_framework_extensions.routers import ExtendedDefaultRouter

from looking_for_group.game_catalog import api_views as catalog_api_views

# API Router
catalog_router = ExtendedDefaultRouter()
catalog_router.register(
    r"publishers", catalog_api_views.GamePublisherViewSet, basename="api-publisher"
)
catalog_router.register(
    r"systems", catalog_api_views.GameSystemViewSet, basename="api-system"
)
catalog_router.register(
    r"editions", catalog_api_views.WideGameEditionViewSet, basename="api-wideedition"
)
catalog_router.register(
    r"modules",
    catalog_api_views.WidePublishedModuleViewSet,
    basename="api-widepublishedmodule",
)
game_router = catalog_router.register(
    r"publishedgames",
    catalog_api_views.PublishedGameViewSet,
    basename="api-publishedgame",
)

edition_router = game_router.register(
    r"editions",
    catalog_api_views.GameEditionViewSet,
    basename="api-edition",
    parents_query_lookups=["game"],
)

edition_router.register(
    r"sourcebooks",
    catalog_api_views.SourcebookViewSet,
    basename="api-sourcebook",
    parents_query_lookups=["edition__game", "edition"],
)

edition_router.register(
    r"publishedmodules",
    catalog_api_views.PublishedModuleViewSet,
    basename="api-publishedmodule",
    parents_query_lookups=["parent_game_edition__game", "parent_game_edition"],
)

urlpatterns = catalog_router.urls
