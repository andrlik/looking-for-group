from django.urls import path

from ..rpgcollections import views as coll_views
from . import views

app_name = "gamer_profiles"
urlpatterns = [
    path("communities/", view=views.CommunityListView.as_view(), name="community-list"),
    path(
        "communities/create/",
        view=views.CommunityCreateView.as_view(),
        name="community-create",
    ),
    path(
        "communities/<slug:community>/edit/",
        view=views.CommunityUpdateView.as_view(),
        name="community-edit",
    ),
    path(
        "communities/<slug:community>/",
        view=views.CommunityDetailView.as_view(),
        name="community-detail",
    ),
    path(
        "communities/<slug:community>/delete/",
        view=views.CommunityDeleteView.as_view(),
        name="community-delete",
    ),
    path(
        "communities/<slug:community>/transfer/",
        view=views.TransferCommunityOwnership.as_view(),
        name="community-transfer-owner",
    ),
    path(
        "communities/<slug:community>/member/<slug:gamer>/edit/",
        view=views.ChangeCommunityRole.as_view(),
        name="community-edit-gamer-role",
    ),
    path(
        "communities/<slug:community>/apply/",
        view=views.CreateApplication.as_view(),
        name="community-apply",
    ),
    path(
        "communities/<slug:community>/join/",
        view=views.JoinCommunity.as_view(),
        name="community-join",
    ),
    path(
        "communities/<slug:community>/discord/",
        view=views.CommunityDiscordLinkView.as_view(),
        name="community-discord-link",
    ),
    path(
        "communities/<slug:community>/leave/",
        view=views.LeaveCommunity.as_view(),
        name="community-leave",
    ),
    path(
        "communities/<slug:community>/members/",
        view=views.CommunityMemberList.as_view(),
        name="community-member-list",
    ),
    path(
        "communities/<slug:community>/applicants/",
        view=views.CommunityApplicantList.as_view(),
        name="community-applicant-list",
    ),
    path(
        "communities/<slug:community>/applicants/<uuid:application>/",
        view=views.CommunityApplicantDetail.as_view(),
        name="community-applicant-detail",
    ),
    path(
        "communities/<slug:community>/applicants/<uuid:application>/approve/",
        view=views.ApproveApplication.as_view(),
        name="community-applicant-approve",
    ),
    path(
        "communities/<slug:community>/applicants/<uuid:application>/reject/",
        view=views.RejectApplication.as_view(),
        name="community-applicant-reject",
    ),
    path(
        "communities/<slug:community>/kicks/",
        view=views.CommunityKickedUserList.as_view(),
        name="community-kick-list",
    ),
    path(
        "communities/<slug:community>/members/<slug:gamer>/kick/",
        view=views.CommunityKickUser.as_view(),
        name="community-kick-gamer",
    ),
    path(
        "communities/<slug:community>/kicks/<uuid:kick>/edit/",
        view=views.UpdateKickRecord.as_view(),
        name="community-kick-edit",
    ),
    path(
        "communities/<slug:community>/kicks/<uuid:kick>/delete/",
        view=views.DeleteKickRecord.as_view(),
        name="community-kick-delete",
    ),
    path(
        "communities/<slug:community>/bans/",
        view=views.CommunityBannedUserList.as_view(),
        name="community-ban-list",
    ),
    path(
        "communities/<slug:community>/members/<slug:gamer>/ban/",
        view=views.CommunityBanUser.as_view(),
        name="community-ban-gamer",
    ),
    path(
        "communities/<slug:community>/bans/<uuid:ban>/edit/",
        view=views.CommunityUpdateBan.as_view(),
        name="community-ban-edit",
    ),
    path(
        "communities/<slug:community>/bans/<uuid:ban>/delete/",
        view=views.CommunityDeleteBan.as_view(),
        name="community-ban-delete",
    ),
    path(
        "communities/<slug:slug>/invites/",
        view=views.CommunityInviteList.as_view(),
        name="community_invite_list",
    ),
    path(
        "profiles/<slug:gamer>/",
        view=views.GamerProfileDetailView.as_view(),
        name="profile-detail",
    ),
    path(
        "profiles/<slug:gamer>/collection/",
        view=coll_views.BookListView.as_view(),
        name="book-list",
    ),
    path("me/edit/", view=views.GamerProfileUpdateView.as_view(), name="profile-edit"),
    path(
        "profiles/<slug:gamer>/add_note/",
        view=views.CreateGamerNote.as_view(),
        name="add-gamer-note",
    ),
    path(
        "me/notes/<uuid:gamernote>/edit/",
        view=views.UpdateGamerNote.as_view(),
        name="edit-gamernote",
    ),
    path(
        "me/notes/<uuid:gamernote>/delete/",
        view=views.RemoveGamerNote.as_view(),
        name="delete-gamernote",
    ),
    path(
        "profiles/<slug:gamer>/friend/",
        view=views.GamerFriendRequestView.as_view(),
        name="gamer-friend",
    ),
    path(
        "me/requests/<uuid:friend_request>/withdraw/",
        view=views.GamerFriendRequestWithdraw.as_view(),
        name="gamer-friend-request-delete",
    ),
    path(
        "me/requests/<uuid:friend_request>/approve/",
        view=views.GamerFriendRequestApprove.as_view(),
        name="gamer-friend-request-approve",
    ),
    path(
        "me/requests/<uuid:friend_request>/reject/",
        view=views.GamerFriendRequestReject.as_view(),
        name="gamer-friend-request-reject",
    ),
    path(
        "me/requests/",
        view=views.GamerFriendRequestListView.as_view(),
        name="my-gamer-friend-requests",
    ),
    path(
        "profiles/<slug:gamer>/mute/", view=views.MuteGamer.as_view(), name="mute-gamer"
    ),
    path(
        "profiles/<slug:gamer>/mute/?next=<path:next>",
        view=views.MuteGamer.as_view(),
        name="mute-gamer",
    ),
    path(
        "me/mutes/<uuid:mute>/unmute/",
        view=views.RemoveMute.as_view(),
        name="unmute-gamer",
    ),
    path(
        "me/mutes/<uuid:mute>/unmute/?next=<path:next>",
        view=views.RemoveMute.as_view(),
        name="unmute-gamer",
    ),
    path("me/mutes/", view=views.MyMuteList.as_view(), name="my-mute-list"),
    path("me/blocks/", view=views.BlockList.as_view(), name="my-block-list"),
    path(
        "profiles/<slug:gamer>/block/",
        view=views.BlockGamer.as_view(),
        name="block-gamer",
    ),
    path(
        "profiles/<slug:gamer>/block/?next=<path:next>",
        view=views.BlockGamer.as_view(),
        name="block-gamer",
    ),
    path(
        "profiles/<slug:gamer>/export/",
        view=views.ExportProfileView.as_view(),
        name="profile_export",
    ),
    path(
        "me/blocks/<uuid:block>/unblock/",
        view=views.RemoveBlock.as_view(),
        name="unblock-gamer",
    ),
    path(
        "me/blocks/<uuid:block>/unblock/?next=<path:next>",
        view=views.RemoveBlock.as_view(),
        name="unblock-gamer",
    ),
    path(
        "me/communities/",
        view=views.MyCommunitiesListView.as_view(),
        name="my-community-list",
    ),
    path(
        "me/applications/community/",
        view=views.MyApplicationList.as_view(),
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
    path(
        "me/available/",
        view=views.GamerAvailabilityUpdate.as_view(),
        name="set-available",
    ),
]
