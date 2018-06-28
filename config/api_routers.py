from rest_framework.routers import DefaultRouter
from looking_for_group.game_catalog import api_views as catalog_api_views
from looking_for_group.gamer_profiles import api_views as profile_api_views


# API Router
router = DefaultRouter()
router.register(
    r"catalog/publishers",
    catalog_api_views.GamePublisherViewSet,
    base_name="api-publisher",
)
router.register(
    r"catalog/systems", catalog_api_views.GameSystemViewSet, base_name="api-system"
)
router.register(
    r"catalog/publishedgames",
    catalog_api_views.PublishedGameViewSet,
    base_name="api-publishedgame",
)
router.register(
    r"catalog/publishedmodules",
    catalog_api_views.PublishedModuleViewSet,
    base_name="api-publishedmodule",
)
router.register(
    r"social/communities",
    profile_api_views.GamerCommunityViewSet,
    base_name="api-community",
)
router.register(
    r"social/profiles", profile_api_views.GamerProfileViewSet, base_name="api-profile"
)
router.register(
    r"social/memberships",
    profile_api_views.CommunityMembershipViewSet,
    base_name="api-memberships",
)
router.register(
    r"social/applications",
    profile_api_views.CommunityApplicationViewSet,
    base_name="api-comm_applications",
)
router.register(
    r"social/gamernotes", profile_api_views.GamerNoteViewSet, base_name="api-gamernotes"
)
router.register(
    r"social/gamerrating",
    profile_api_views.GamerRatingViewSet,
    base_name="api-gamerrating",
)
