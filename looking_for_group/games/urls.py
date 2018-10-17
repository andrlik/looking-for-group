from django.urls import path

from . import views
from .feeds import GamesICalFeed, UpcomingGamesFeed

app_name = "games"

urlpatterns = [
    path(
        "schedule/api/occurrences/",
        views.CalendarJSONView.as_view(),
        name="api_occurrences",
    ),
    path(
        "schedule/feed/calendar/upcoming/<uuid:gamer>/",
        UpcomingGamesFeed(),
        name="upcoming_events_feed",
    ),
    path(
        "schedule/ical/calendar/<uuid:gamer>/",
        GamesICalFeed(),
        name="calendar_ical",
    ),
    path("schedule/calendar/", views.CalendarDetail.as_view(), name="calendar_detail"),
    path(
        "sessions/<slug:session>/",
        views.GameSessionDetail.as_view(),
        name="session_detail",
    ),
    path(
        "sessions/<slug:session>/edit/",
        views.GameSessionUpdate.as_view(),
        name="session_edit",
    ),
    path(
        "sessions/<slug:session>/delete/",
        views.GameSessionDelete.as_view(),
        name="session_delete",
    ),
    path(
        "game/<slug:gameid>/sessions/",
        views.GameSessionList.as_view(),
        name="session_list_for_game",
    ),
    path(
        "game/<slug:gameid>/logs/",
        views.AdventureLogList.as_view(),
        name="log_list_for_game",
    ),
    path(
        "game/<slug:gameid>/logs/<uuid:log>/",
        views.AdventureLogDetail.as_view(),
        name="log_detail",
    ),
    path(
        "game/<slug:gameid>/logs/<uuid:log>/edit/",
        views.AdventureLogUpdate.as_view(),
        name="log_edit",
    ),
    path(
        "game/<slug:gameid>/logs/<uuid:log>/delete/",
        views.AdventureLogDelete.as_view(),
        name="log_delete",
    ),
    path(
        "game/<slug:gameid>/", views.GamePostingDetailView.as_view(), name="game_detail"
    ),
    path(
        "game/<slug:gameid>/edit/",
        views.GamePostingUpdateView.as_view(),
        name="game_edit",
    ),
    path(
        "game/<slug:gameid>/delete/",
        views.GamePostingDeleteView.as_view(),
        name="game_delete",
    ),
    path("game/create/", views.GamePostingCreateView.as_view(), name="game_create"),
    path("/", views.GamePostingListView.as_view(), name="game_list"),
]
