from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views, api_views

app_name = "game_catalog"
urlpatterns = [
    path("publishers/", view=views.GamePublisherListView.as_view(), name="pub_list"),
    path(
        "publishers/<uuid:publisher>/",
        view=views.GamePublisherDetailView.as_view(),
        name="pub_detail",
    ),
    path("systems/", view=views.GameSystemListView.as_view(), name="system_list"),
    path(
        "systems/<uuid:system>/",
        view=views.GameSystemDetailView.as_view(),
        name="system_detail",
    ),
    path(
        "publishedgames/", view=views.PublishedGameListView.as_view(), name="game_list"
    ),
    path(
        "publishedgames/<uuid:game>/",
        view=views.PublishedGameDetailView.as_view(),
        name="game_detail",
    ),
    path(
        "publishedmodules/",
        view=views.PublishedModuleListView.as_view(),
        name="module_list",
    ),
    path(
        "publishedmodules/<uuid:module>/",
        view=views.PublishedModuleDetailView.as_view(),
        name="module_detail",
    ),
]


# API Router
router = DefaultRouter()
router.register(r'publishers', api_views.GamePublisherViewSet)
router.register(r'systems', api_views.GameSystemViewSet)
router.register(r'publishedgames', api_views.PublishedGameViewSet)
router.register(r'publishedmodules', api_views.PublishedModuleViewSet)
