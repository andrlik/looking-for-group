from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from looking_for_group.gamer_profiles import api_views as profile_api_views

# API Router

social_router = DefaultRouter()
social_router.register(
    r"communities", profile_api_views.GamerCommunityViewSet, base_name="api-community"
)
community_router = routers.NestedDefaultRouter(
    social_router, r"communities", lookup="community"
)
community_router.register(
    r"memberships",
    profile_api_views.CommunityMembershipViewSet,
    base_name="api-memberships",
)
community_router.register(
    r"applications",
    profile_api_views.CommunityAdminApplicationViewSet,
    base_name="api-comm-applications",
)
social_router.register(
    r"profiles", profile_api_views.GamerProfileViewSet, base_name="api-profile"
)
profile_router = routers.NestedDefaultRouter(
    social_router, r"profiles", lookup="profile"
)
profile_router.register(
    r"notes", profile_api_views.GamerNoteViewSet, base_name="api-gamernotes"
)
social_router.register(
    r"applications",
    profile_api_views.CommunityApplicationViewSet,
    base_name="api-my-applications",
)
social_router.register(
    r"friendrequests/sent",
    profile_api_views.SentFriendRequestViewSet,
    base_name="api-my-sent-requests",
)
social_router.register(
    r"friendrequests/received",
    profile_api_views.ReceivedFriendRequestViewset,
    base_name="api-my-received-requests",
)

urlpatterns = [
    path("", include(social_router.urls)),
    path("", include(community_router.urls)),
    path("", include(profile_router.urls)),
]
