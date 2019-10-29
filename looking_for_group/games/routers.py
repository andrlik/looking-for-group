from rest_framework_extensions.routers import ExtendedDefaultRouter

from . import api_views

games_app_router = ExtendedDefaultRouter()

games_router = games_app_router.register(
    r"games", api_views.GamePostingViewSet, basename="api-game"
)

session_router = games_router.register(
    r"sessions",
    api_views.GameSessionViewSet,
    basename="api-session",
    parents_query_lookups=["game__slug"],
)

session_router.register(
    r"log",
    api_views.AdventureLogViewSet,
    basename="api-adventurelog",
    parents_query_lookups=["session__game__slug", "session__slug"],
)
