from rest_framework_extensions.routers import ExtendedDefaultRouter

from .views import api_views as profile_api_views

# API Router

social_router = ExtendedDefaultRouter()
community_router = social_router.register(
    r"social/communities",
    profile_api_views.GamerCommunityViewSet,
    basename="api-community",
)
community_router.register(
    r"members",
    profile_api_views.CommunityMembershipViewSet,
    basename="api-member",
    parents_query_lookups=["community"],
)
community_router.register(
    r"applications",
    profile_api_views.CommunityAdminApplicationViewSet,
    basename="api-comm-application",
    parents_query_lookups=["community"],
)
community_router.register(
    r"kicks",
    profile_api_views.KickedUserViewSet,
    basename="api-comm-kick",
    parents_query_lookups=["community"],
)
community_router.register(
    r"bans",
    profile_api_views.BannedUserViewSet,
    basename="api-comm-ban",
    parents_query_lookups=["community"],
)
profile_router = social_router.register(
    r"social/profiles", profile_api_views.GamerProfileViewSet, basename="api-profile"
)

profile_router.register(
    r"notes",
    profile_api_views.GamerNoteViewSet,
    basename="api-gamernote",
    parents_query_lookups=["gamer"],
)
social_router.register(
    r"social/applications",
    profile_api_views.CommunityApplicationViewSet,
    basename="api-my-application",
)
social_router.register(
    r"social/friendrequests/sent",
    profile_api_views.SentFriendRequestViewSet,
    basename="api-my-sent-request",
)
social_router.register(
    r"social/friendrequests/received",
    profile_api_views.ReceivedFriendRequestViewset,
    basename="api-my-received-request",
)
social_router.register(
    r"social/blocks", profile_api_views.BlockedUserViewSet, basename="api-block"
)
social_router.register(
    r"social/mutes", profile_api_views.MutedUserViewSet, basename="api-mute"
)
urlpatterns = social_router.urls
