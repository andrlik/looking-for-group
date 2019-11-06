from rest_framework_extensions.routers import ExtendedDefaultRouter

from . import api_views

games_app_router = ExtendedDefaultRouter()

games_app_router.register(
    r"games/my-applications",
    api_views.GameApplicationViewSet,
    basename="api-mygameapplication",
)

games_app_router.register(
    r"games/my-characters", api_views.MyCharacterViewSet, basename="api-mycharacter"
)


games_router = games_app_router.register(
    r"games", api_views.GamePostingViewSet, basename="api-game"
)

games_router.register(
    r"applications",
    api_views.GMGameApplicationViewSet,
    basename="api-gameapplication",
    parents_query_lookups=["game__slug"],
)

games_router.register(
    r"characters",
    api_views.CharacterViewSet,
    basename="api-character",
    parents_query_lookups=["game__slug"],
)

games_router.register(
    r"players",
    api_views.PlayerViewSet,
    basename="api-player",
    parents_query_lookups=["game__slug"],
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
