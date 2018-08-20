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
    path("profiles/<uuid:gamer>/add_note/", view=views.CreateGamerNote.as_view(), name='add-gamer-note'),
    path("profiles/<uuid:gamernote>/delete/", view=views.RemoveGamerNote.as_view(), name='delete-gamernote'),
    path(
        "profiles/<uuid:gamer>/friend/",
        view=views.GamerFriendRequestView.as_view(),
        name="gamer-friend",
    ),
    path(
        "profiles/requests/<uuid:friend_request>/withdraw/",
        view=views.GamerFriendRequestWithdraw.as_view(),
        name="gamer-friend-request-delete",
    ),
    path(
        "profiles/requests/<uuid:friend_request>/approve/",
        view=views.GamerFriendRequestApprove.as_view(),
        name="gamer-friend-request-approve",
    ),
    path(
        "profiles/requests/<uuid:friend_request>/reject/",
        view=views.GamerFriendRequestReject.as_view(),
        name="gamer-friend-request-reject",
    ),
    path(
        "profiles/requests/",
        view=views.GamerFriendRequestListView.as_view(),
        name="my-gamer-friend-requests",
    ),
    path(
        "profiles/<uuid:gamer>/mute/", view=views.MuteGamer.as_view(), name="mute-gamer"
    ),
    path(
        "profiles/<uuid:gamer>/mute/?next=<path:next>",
        view=views.MuteGamer.as_view(),
        name="mute-gamer",
    ),
    path(
        "profiles/mutes/<uuid:mute>/unmute/",
        view=views.RemoveMute.as_view(),
        name="unmute-gamer",
    ),
    path(
        "profiles/mutes/<uuid:mute>/unmute/?next=<path:next>",
        view=views.RemoveMute.as_view(),
        name="unmute-gamer",
    ),
    path("profiles/mutes/", view=views.MyMuteList.as_view(), name="my-mute-list"),
    path("profiles/blocks/", view=views.BlockList.as_view(), name="my-block-list"),
    path("profiles/<uuid:gamer>/block/", view=views.BlockGamer.as_view(), name='block-gamer'),
    path("profiles/<uuid:gamer>/block/?next=<path:next>", view=views.BlockGamer.as_view(), name='block-gamer'),
    path("profiles/blocks/<uuid:block>/unblock/", view=views.RemoveBlock.as_view(), name='unblock-gamer'),
    path("profiles/blocks/<uuid:block>/unblock/?next=<path:next>", view=views.RemoveBlock.as_view(), name='unblock-gamer'),
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
