from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api_views, views

app_name = "game_catalog"
urlpatterns = [
    path("publishers/", view=views.GamePublisherListView.as_view(), name="pub-list"),
    path(
        "publishers/create/",
        view=views.GamePublisherCreateView.as_view(),
        name="pub-create",
    ),
    path(
        "publishers/page<int:page>/",
        view=views.GamePublisherListView.as_view(),
        name="pub-list",
    ),
    path(
        "publishers/<uuid:publisher>/",
        view=views.GamePublisherDetailView.as_view(),
        name="pub-detail",
    ),
    path(
        "publishers/<uuid:publisher>/edit/",
        view=views.GamePublisherUpdateView.as_view(),
        name="pub-edit",
    ),
    path(
        "publishers/<uuid:publisher>/delete/",
        view=views.GamePublisherDeleteView.as_view(),
        name="pub-delete",
    ),
    path("systems/", view=views.GameSystemListView.as_view(), name="system-list"),
    path(
        "systems/create/",
        view=views.GameSystemCreateView.as_view(),
        name="system-create",
    ),
    path(
        "systems/page<int:page>/",
        view=views.GameSystemListView.as_view(),
        name="system-list",
    ),
    path(
        "systems/<uuid:system>/",
        view=views.GameSystemDetailView.as_view(),
        name="system-detail",
    ),
    path(
        "systems/<uuid:system>/edit/",
        view=views.GameSystemUpdateView.as_view(),
        name="system-edit",
    ),
    path(
        "systems/<uuid:system>/delete/",
        view=views.GameSystemDeleteView.as_view(),
        name="system-delete",
    ),
    path(
        "publishedgames/create/",
        view=views.PublishedGameCreateView.as_view(),
        name="game-create",
    ),
    path(
        "publishedgames/", view=views.PublishedGameListView.as_view(), name="game-list"
    ),
    path(
        "publishedgames/page<int:page>/",
        views.PublishedGameListView.as_view(),
        name="game-list",
    ),
    path(
        "publishedgames/<uuid:game>/",
        view=views.PublishedGameDetailView.as_view(),
        name="game-detail",
    ),
    path(
        "publishedgames/<uuid:game>/edit/",
        view=views.PublishedGameUpdateView.as_view(),
        name="game-edit",
    ),
    path(
        "publishedgames/<uuid:game>/delete/",
        view=views.PublishedGameDeleteView.as_view(),
        name="game-delete",
    ),
    path(
        "publishedgames/<uuid:game>/editions/create/",
        view=views.EditionCreateView.as_view(),
        name="edition_create",
    ),
    path(
        "editions/<slug:edition>/",
        view=views.EditionDetailView.as_view(),
        name="edition_detail",
    ),
    path(
        "editions/<slug:edition>/edit/",
        view=views.EditionUpdateView.as_view(),
        name="edition_edit",
    ),
    path(
        "editions/<slug:edition>/delete/",
        view=views.EditionDeleteView.as_view(),
        name="edition_delete",
    ),
    path(
        "editions/<slug:edition>/sourcebooks/create/",
        view=views.SourceBookCreateView.as_view(),
        name="sourcebook_create",
    ),
    path(
        "editions/<slug:edition>/publishedmodules/create/",
        view=views.PublishedModuleCreateView.as_view(),
        name="module-create",
    ),
    path(
        "sourcebooks/<slug:book>/",
        view=views.SourceBookDetailView.as_view(),
        name="sourcebook_detail",
    ),
    path(
        "sourcebooks/<slug:book>/edit/",
        view=views.SourceBookUpdateView.as_view(),
        name="sourcebook_edit",
    ),
    path(
        "sourcebooks/<slug:book>/delete/",
        view=views.SourceBookDeleteView.as_view(),
        name="sourcebook_delete",
    ),
    path(
        "publishedmodules/",
        view=views.PublishedModuleListView.as_view(),
        name="module-list",
    ),
    path(
        "publishedmodules/page<int:page>/",
        view=views.PublishedModuleListView.as_view(),
        name="module-list",
    ),
    path(
        "publishedmodules/<uuid:module>/",
        view=views.PublishedModuleDetailView.as_view(),
        name="module-detail",
    ),
    path(
        "publishedmodules/<uuid:module>/edit/",
        view=views.PublishedModuleUpdateView.as_view(),
        name="module-edit",
    ),
    path(
        "publishedmodules/<uuid:module>/delete/",
        view=views.PublishedModuleDeleteView.as_view(),
        name="module-delete",
    ),
]


# API Router
router = DefaultRouter()
router.register(r"publishers", api_views.GamePublisherViewSet)
router.register(r"systems", api_views.GameSystemViewSet)
router.register(r"publishedgames", api_views.PublishedGameViewSet)
router.register(r"publishedmodules", api_views.PublishedModuleViewSet)
