from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework_extensions.routers import ExtendedDefaultRouter

from looking_for_group.game_catalog.routers import catalog_router
from looking_for_group.gamer_profiles.routers import social_router
from looking_for_group.games.routers import games_app_router

api_router = ExtendedDefaultRouter()
api_router.registry.extend(catalog_router.registry)
api_router.registry.extend(social_router.registry)
api_router.registry.extend(games_app_router.registry)

schema_view = get_schema_view(
    openapi.Info(
        title="LFG Directory API",
        default_version="v1",
        description="LFG API for group finding, communities, and campaign management.",
        terms_of_service="https://www.lfg.directory/terms/",
        contact=openapi.Contact(email="daniel@mg.lfg.directory"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(IsAuthenticated,),
)

urlpatterns = [
    path("", include(api_router.urls)),
    path(
        "swagger.<str:format>",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
