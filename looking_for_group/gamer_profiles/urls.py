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
    path(
        "communities/<uuid:community>/applicants/",
        view=views.CommunityApplicantList.as_view(),
        name="community-applicant-list",
    ),
    path(
        "communities/<uuid:community>/applicants/<uuid:application>/",
        view=views.CommunityApplicantDetail.as_view(),
        name="community-applicant-detail",
    ),
    path(
        "communities/<uuid:community>/applicants/<uuid:application>/approve/",
        view=views.ApproveApplication.as_view(),
        name="community-applicant-approve",
    ),
    path(
        "communities/<uuid:community>/applicants/<uuid:application>/reject/",
        view=views.RejectApplication.as_view(),
        name="community-applicant-reject",
    ),
    path(
        "profiles/<uuid:gamer>/",
        view=views.GamerProfileDetailView.as_view(),
        name="profile-detail",
    ),
    path(
        "me/applications/community/",
        view=views.CreateApplication.as_view(),
        name="my-application-list",
    ),
    path(
        "me/applications/community/<uuid:application>/edit/",
        view=views.UpdateApplication.as_view(),
        name="update-application",
    ),
    path(
        "me/applications/community/<uuid:application>/delete/",
        view=views.WithdrawApplication.as_view(),
        name="delete-application",
    ),
]
