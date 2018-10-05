from django.urls import path

from . import views
from .feeds import CalendarICalendar, UpcomingEventsFeed

app_name = "looking_for_group.games"

urlpatterns = [
    path(
        "schedule/api/occurrences/",
        views.CalendarJSONView.as_view(),
        name="api_occurrences",
    ),
    path(
        "schedule/feed/calendar/upcoming/<uuid:gamer>/",
        UpcomingEventsFeed(),
        name="upcoming_events_feed",
    ),
    path(
        "schedule/ical/calendar/<uuid:gamer>/",
        CalendarICalendar(),
        name="calendar_ical",
    ),
    path("schedule/calendar/", views.CalendarDetail.as_view(), name="calendar_detail"),
    path(
        "sessions/<uuid:session>/",
        views.GameSessionDetail.as_view(),
        name="session_detail",
    ),
    path(
        "sessions/<uuid:session>/edit/",
        views.GameSessionUpdate.as_view(),
        name="session_edit",
    ),
    path(
        "sessions/<uuid:session>/delete/",
        views.GameSessionDelete.as_view(),
        name="session_delete",
    ),
    path(
        "game/<uuid:gameid>/sessions/",
        views.GameSessionList.as_view(),
        name="session_list_for_game",
    ),
    path(
        "game/<uuid:gameid>/logs/",
        views.AdventureLogList.as_view(),
        name="log_list_for_game",
    ),
    path(
        "game/<uuid:gameid>/logs/<uuid:log>/",
        views.AdventureLogDetail.as_view(),
        name="log_detail",
    ),
    path(
        "game/<uuid:gameid>/logs/<uuid:log>/edit/",
        views.AdventureLogUpdate.as_view(),
        name="log_edit",
    ),
    path(
        "game/<uuid:gameid>/logs/<uuid:log>/delete/",
        views.AdventureLogDelete.as_view(),
        name="log_delete",
    ),
    path(
        "game/<uuid:gameid>/", views.GamePostingDetailView.as_view(), name="game_detail"
    ),
    path(
        "game/<uuid:gameid>/edit/",
        views.GamePostingUpdateView.as_view(),
        name="game_edit",
    ),
    path(
        "game/<uuid:gameid>/delete/",
        views.GamePostingDeleteView.as_view(),
        name="game_delete",
    ),
    path("game/create/", views.GamePostingCreateView.as_view(), name="game_create"),
    path("/", views.GamePostingListView.as_view(), name="game_list"),
]
