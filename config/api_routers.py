from django.urls import include, path
from rest_framework_extensions.routers import ExtendedDefaultRouter

from looking_for_group.game_catalog.routers import catalog_router
from looking_for_group.gamer_profiles.routers import social_router

api_router = ExtendedDefaultRouter()
api_router.registry.extend(catalog_router.registry)
api_router.registry.extend(social_router.registry)


urlpatterns = [path("", include(api_router.urls))]
