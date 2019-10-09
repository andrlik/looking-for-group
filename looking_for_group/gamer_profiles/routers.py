from django.urls import include, path
from rest_framework_nested import routers

from looking_for_group.gamer_profiles import api_views as profile_api_views

# API Router

social_router = routers.SimpleRouter()
social_router.register(
    r"communities", profile_api_views.GamerCommunityViewSet, base_name="api-community"
)
community_router = routers.NestedSimpleRouter(
    social_router, r"communities", lookup="community"
)
membership_router = routers.NestedSimpleRouter(
    community_router, r"members", lookup="member"
)
membership_router.register(
    r"memberships",
    profile_api_views.CommunityMembershipViewSet,
    base_name="api-memberships",
)
application_router = routers.NestedSimpleRouter(
    community_router, r"applications", lookup="application"
)
application_router.register(
    r"applications",
    profile_api_views.CommunityApplicationViewSet,
    base_name="api-comm_applications",
)
social_router.register(
    r"profiles", profile_api_views.GamerProfileViewSet, base_name="api-profile"
)
profile_router = routers.NestedSimpleRouter(
    social_router, r"profiles", lookup="profile"
)
note_router = routers.NestedSimpleRouter(profile_router, r"notes", lookup="note")
note_router.register(
    r"gamernotes", profile_api_views.GamerNoteViewSet, base_name="api-gamernotes"
)

urlpatterns = [
    path("", include(social_router.urls)),
    path("", include(community_router.urls)),
    path("", include(membership_router.urls)),
    path("", include(application_router.urls)),
    path("", include(profile_router.urls)),
    path("", include(note_router.urls)),
]
