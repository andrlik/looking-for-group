from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from looking_for_group.game_catalog import api_views as catalog_api_views

# API Router
catalog_router = DefaultRouter()
catalog_router.register(
    r"publishers", catalog_api_views.GamePublisherViewSet, base_name="api-publisher"
)
catalog_router.register(
    r"systems", catalog_api_views.GameSystemViewSet, base_name="api-system"
)
catalog_router.register(
    r"publishedgames",
    catalog_api_views.PublishedGameViewSet,
    base_name="api-publishedgame",
)
edition_router = routers.NestedDefaultRouter(
    catalog_router, r"publishedgames", lookup="publishedgame"
)
edition_router.register(
    r"editions", catalog_api_views.GameEditionViewSet, base_name="api-edition"
)
sourcebook_router = routers.NestedDefaultRouter(
    edition_router, r"editions", lookup="edition"
)
sourcebook_router.register(
    r"sourcebooks", catalog_api_views.SourcebookViewSet, base_name="api-sourcebook"
)
module_router = routers.NestedDefaultRouter(
    edition_router, r"editions", lookup="edition"
)
module_router.register(
    r"publishedmodules",
    catalog_api_views.PublishedModuleViewSet,
    base_name="api-publishedmodule",
)

urlpatterns = [
    path("", include(catalog_router.urls)),
    path("", include(edition_router.urls)),
    path("", include(sourcebook_router.urls)),
    path("", include(module_router.urls)),
]
