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
    path("schedule/ical/calendar/<uuid:gamer>/", GamesICalFeed(), name="calendar_ical"),
    path("schedule/calendar/", views.CalendarDetail.as_view(), name="calendar_detail"),
    path(
        "sessions/<slug:session>/",
        view=views.GameSessionDetail.as_view(),
        name="session_detail",
    ),
    path(
        "sessions/<slug:session>/edit/",
        view=views.GameSessionUpdate.as_view(),
        name="session_edit",
    ),
    path(
        "sessions/<slug:session>/move/",
        view=views.GameSessionMove.as_view(),
        name="session_move",
    ),
    path(
        "sessions/<slug:session>/cancel/",
        view=views.GameSessionCancel.as_view(),
        name="session_cancel",
    ),
    path("sessions/<slug:session>/uncancel/", view=views.GameSessionUncancel.as_view(), name='session_uncancel'),
    path(
        "game/<slug:gameid>/sessions/",
        view=views.GameSessionList.as_view(),
        name="session_list",
    ),
    path(
        "game/<slug:gameid>/sessions/create/",
        view=views.GameSessionCreate.as_view(),
        name="session_create",
    ),
    path(
        "logs/<slug:log>/edit/",
        view=views.AdventureLogUpdate.as_view(),
        name="log_edit",
    ),
    path(
        "logs/<slug:log>/delete/",
        view=views.AdventureLogDelete.as_view(),
        name="log_delete",
    ),
    path(
        "logs/<slug:session>/create/",
        view=views.AdventureLogCreate.as_view(),
        name="log_create",
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
    path(
        "game/<slug:gameid>/apply/",
        views.GamePostingApplyView.as_view(),
        name="game_apply",
    ),
    path(
        "applications/<slug:application>/",
        views.GamePostingApplicationDetailView.as_view(),
        name="game_apply_detail",
    ),
    path(
        "applications/<slug:application>/edit/",
        views.GamePostingApplicationUpdateView.as_view(),
        name="game_apply_update",
    ),
    path(
        "applications/<slug:application>/delete/",
        views.GamePostingWithdrawApplication.as_view(),
        name="game_apply_delete",
    ),
    path(
        "applications/",
        views.GamePostingAppliedList.as_view(),
        name="my-game-applications",
    ),
    path(
        "game/<slug:game>/<slug:player>/characters/create/",
        views.CharacterCreate.as_view(),
        name="character_create",
    ),
    path(
        "character/<slug:character>/",
        views.CharacterDetail.as_view(),
        name="character_detail",
    ),
    path(
        "character/<slug:character>/edit/",
        views.CharacterUpdate.as_view(),
        name="character_update",
    ),
    path(
        "character/<slug:character>/delete/",
        views.CharacterDelete.as_view(),
        name="character_delete",
    ),
    path(
        "game/<slug:game>/<slug:player>/leave/",
        views.PlayerLeaveGameView.as_view(),
        name="player_leave",
    ),
    path(
        "game/<slug:game>/<slug:player>/kick/",
        views.PlayerKickView.as_view(),
        name="player_kick",
    ),
    path("create/", views.GamePostingCreateView.as_view(), name="game_create"),
    path("", views.GamePostingListView.as_view(), name="game_list"),
]
