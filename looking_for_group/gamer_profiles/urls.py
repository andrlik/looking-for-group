from django.urls import path

from . import views

app_name = "gamer_profiles"
urlpatterns = [
    path("communities/", view=views.CommunityListView.as_view(), name="community-list"),
    path(
        "communities/mine/",
        view=views.MyCommunitiesListView.as_view(),
        name="my-community-list",
    ),
    path(
        "communities/<uuid:community>/",
        view=views.CommunityDetailView.as_view(),
        name="community-detail",
    ),
    path(
        "communities/<uuid:community>/apply/",
        view=views.CreateApplication.as_view(),
        name="community-apply",
    ),
    path(
        "communities/<uuid:community>/join/",
        view=views.JoinCommunity.as_view(),
        name="community-join",
    ),
    path(
        "communities/<uuid:community>/leave/",
        view=views.LeaveCommunity.as_view(),
        name="community-leave",
    ),
    path(
        "communities/<uuid:community>/members/",
        view=views.CommunityMemberList.as_view(),
        name="community-member-list",
    ),
    path("profiles/<uuid:gamer>/", view=views.GamerProfileDetailView.as_view(), name='profile-detail'),
]
