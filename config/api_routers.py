from django.urls import include, path

urlpatterns = [
    path("catalog/", include("looking_for_group.game_catalog.routers")),
    #  path("social/", include("looking_for_group.gamer_profiles.routers")),
]
