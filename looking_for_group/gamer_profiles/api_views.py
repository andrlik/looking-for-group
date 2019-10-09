from django.core.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_rules.mixins import PermissionRequiredMixin

from . import models, serializers
from .models import AlreadyInCommunity, CurrentlySuspended, NotInCommunity


class GamerCommunityViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    A view set of GamerCommunity functions.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "community.list_communities"
    queryset = models.GamerCommunity.objects.all()
    serializer_class = serializers.GamerCommunitySerializer

    @action(methods=["post"], detail=True)
    def apply(self, request, **kwargs):
        """
        Apply to this community.
        """
        if not request.user.has_perm("community.apply", self.get_object()):
            return Response(
                {
                    "result": "You do not have the permissions needed to apply to this community."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        message = None
        if "message" in request.data.keys():
            message = request.data["message"]
        application = models.CommunityApplication.objects.create(
            gamer=request.user.gamerprofile,
            commmunity=self.get_object(),
            message=message,
            status="review",
        )
        app_data = serializers.CommunityApplicationSerializer(application)
        return Response(app_data.data, status.HTTP_201_CREATED)

    def destroy(self, request, **kwargs):
        """
        Destroy the community.
        """
        if request.user.has_perm("community.delete_community", self.get_object()):
            return super().destroy(request, **kwargs)
        return Response(
            {
                "result": "You do not have the necessary permissions to delete this community."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def update(self, request, **kwargs):
        if not request.user.has_perm("community.edit_community"):
            return Response(
                {
                    "result": "You do not have the necessary permissions to update this community."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, **kwargs)

    def partial_update(self, request, **kwargs):
        if not request.user.has_perm("community.edit_community", self.get_object()):
            return Response(
                {
                    "result": "You do not have the necessary permissions to update this community."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, **kwargs)

    @action(methods=["get"], detail=True)
    def members(self, request, **kwargs):
        """
        List members of a community.
        """
        community = self.get_object()
        if not request.user.has_perm("community.view_details", community):
            return Response(
                {
                    "result": "You are not a member of this community and cannot view member list."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        member_queryset = (
            models.CommunityMembership.objects.filter(community=community)
            .select_related("gamer")
            .prefetch_related("gamer__user")
            .filter(gamer__user=request.user)
        )
        page = self.paginate_queryset(member_queryset)
        if page is not None:
            member_serials = serializers.CommunityMembershipSerializer(page, many=True)
            return self.get_paginated_response(member_serials.data)
        member_serials = serializers.CommunityMembershipSerializer(
            member_queryset, many=True
        )
        return Response(member_serials.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True)
    def bans(self, request, **kwargs):
        """
        Retrieve a list of banned users for this community.
        """
        community = self.get_object()
        if not request.user.has_perm("community.ban_user", community):
            return Response(
                {"result": "You do not have the permissions to see this data."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ban_list = models.BannedUser.objects.filter(community=community)
        serializer = serializers.BannedUserSerializer(ban_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True)
    def kicks(self, request, **kwargs):
        """
        List users that have been kicked/suspended from community.
        """
        community = self.get_object()
        if not request.user.has_perm("community.kick_user", community):
            return Response(
                {"result": "You do not have the permissions to see this data."},
                status=status.HTTP_403_FORBIDDEN,
            )
        kick_list = models.KickedUser.objects.filter(community=community)
        serializer = serializers.KickedUserSerializer(kick_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True)
    def admins(self, request, **kwargs):
        """
        List community admins.
        """
        community = self.get_object()
        if not request.user.has_perm("community.view_details", community):
            return Response(
                {"result": "You do not have the permissions to see this data."},
                status=status.HTTP_403_FORBIDDEN,
            )
        admins = community.get_admins()
        serializer = serializers.GamerProfileSerializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True)
    def mods(self, request, **kwargs):
        """
        List community moderators.
        """
        community = self.get_object()
        if not request.user.has_perm("community.view_details", community):
            return Response(
                {"result": "You do not have the permissions to see this data."},
                status=status.HTTP_403_FORBIDDEN,
            )
        mods = community.get_moderators()
        serializer = serializers.GamerProfileSerializer(mods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BannedUserViewSet(
    PermissionRequiredMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_required = "community.ban_user"
    object_permission_required = "community.ban_user"
    serializer_class = serializers.BannedUserSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "community"

    def check_object_permissions(self, request, obj):
        new_obj = obj.community
        super().check_object_permissions(request, new_obj)

    def get_queryset(self):
        return models.BannedUser.objects.filter(
            community__in=models.GamerCommunity.objects.filter(
                id__in=[
                    c.community.id
                    for c in models.CommunityMembership.objects.filter(
                        community_role="admin", gamer=self.request.user.gamerprofile
                    )
                ]
            )
        ).select_related("blocker", "blockee")


class KickedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    permission_required = "community.kick_user"
    object_permission_required = "community.kick_user"
    serializer_class = serializers.KickedUserSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "community"

    def check_object_permissions(self, request, obj):
        new_obj = obj.community
        super().check_object_permissions(request, new_obj)

    def get_queryset(self):
        return models.KickedUser.objects.filter(
            community__in=models.GamerCommunity.objects.filter(
                id__in=[
                    c.community.id
                    for c in models.CommunityMembership.objects.filter(
                        community_role="admin", gamer=self.request.user.gamerprofile
                    )
                ]
            )
        ).select_related("kicker", "kickee")


class CommunityMembershipViewSet(
    PermissionRequiredMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset for Community membership.
    """

    permission_required = "community.view_roles"
    object_permission_required = "community.edit_membership"
    serializer_class = serializers.CommunityMembershipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("community", "community_role")

    def check_object_permissions(self, request, obj):
        new_obj = obj.community
        super().check_object_permissions(request, new_obj)

    def get_queryset(self):
        return models.CommunityMembership.objects.filter(
            community=models.GamerCommunity.objects.get(pk=self.kwargs["community_id"])
        ).select_related("gamer", "community")

    @action(methods=["post"], detail=True)
    def kick(self, request, **kwargs):
        community = self.get_object().community
        if not request.user.has_perm("community.kick_user", community):
            return Response(
                {
                    "result": "You do not have the required permissions to kick this user."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        end_date = None
        try:
            reason = self.request.kwargs["reason"]
        except KeyError:
            return Response(status=400)
        if "end_date" in self.request.kwargs.keys():
            end_date = self.request.kwargs["end_date"]
        membership = self.get_object()
        kicker = self.request.user.gamerprofile
        try:
            kick_record = serializers.KickedUserSerializer(
                membership.community.kick_user(
                    kicker, membership.gamer, reason, earliest_reapply=end_date
                )
            )
        except PermissionDenied:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)
        except NotInCommunity:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        return Response(kick_record.data, status=status.HTTP_202_ACCEPTED)

    @action(methods=["post"], detail=True)
    def ban(self, request, **kwargs):
        community = self.get_object().community
        if not request.user.has_perm("community.ban_user", community):
            return Response(
                {
                    "result": "You do not have the required permissions to ban this user."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            reason = self.request.kwargs["reason"]
        except KeyError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        banner = self.request.user.gamerprofile
        membership = self.get_object()
        try:
            ban_record = serializers.BannedUserSerializer(
                membership.community.ban_user(banner, membership.gamer, reason)
            )
        except PermissionDenied:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)
        except NotInCommunity:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ban_record.data, status=status.HTTP_202_ACCEPTED)


class GamerProfileViewSet(
    PermissionRequiredMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset for a gamer profile.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "profile.view_detail"
    serializer_class = serializers.GamerProfileSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = (
        "player_status",
        "will_gm",
        "one_shots",
        "adventures",
        "campaigns",
        "online_games",
        "local_games",
        "preferred_games",
        "preferred_systems",
        "adult_themes",
    )

    def get_queryset(self):
        qs_public = models.GamerProfile.objects.filter(private=False).select_related(
            "user"
        )
        qs_friends = self.request.user.gamerprofile.friends.all()
        qs_community = models.GamerProfile.objects.filter(
            id__in=[
                cm.gamer.id
                for cm in models.CommunityMembership.objects.filter(
                    community__in=self.request.user.gamerprofile.communities.all()
                )
            ]
        )
        qs_pub_friends = qs_public.union(qs_friends)
        qs_combined = qs_pub_friends.union(qs_community)
        qs_remove_blocked = qs_combined.exclude(
            id__in=[
                b.blocker.id
                for b in models.BlockedUser.objects.filter(
                    blockee=self.request.user.gamerprofile
                )
            ]
        )
        return qs_remove_blocked

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("profile.edit_profile", self.get_object()):
            return Response(
                {"result": "You cannot edit another user's profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("profile.edit_profile", self.get_object()):
            return Response(
                {"result": "You cannot edit another user's profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        super().partial_update(request, *args, **kwargs)

    # @action_permission_required(
    #     "profile.view_note",
    #     fn=lambda request, **kwargs: models.GamerNote.objects.filter(
    #         author=request.user, gamer=models.GamerProfile.objects.get(pk=pk)
    #     ),
    # )
    # @action(methods=["get"], detail=True)
    # def view_notes(self, request, **kwargs):
    #     notes = models.GamerNote.objects.filter(
    #         author=self.request.user, gamer=self.get_object()
    #     )
    #     serializer = serializers.GamerNoteSerializer(notes, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK)


class GamerNoteViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    Generic view set for gamer notes.
    """

    permission_required = "community.edit_profile_note"
    serializer_class = serializers.GamerNoteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "gamer"

    def get_queryset(self):
        return (
            models.GamerNote.objects.filter(
                gamer=models.GamerProfile.objects.get(pk=self.kwargs["gamer_id"])
            )
            .filter(author=self.request.user.gamerprofile)
            .select_related("author", "gamer", "gamer__user")
        )


class BlockedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View for other users that the individual has blocked.
    """

    permission_required = "profile.remove_block"
    serializer_class = serializers.BlockedUserSerializer

    def get_queryset(self):
        models.BlockedUser.objects.filter(
            blocker=self.request.user.gamerprofile
        ).select_related("blocker", "blocked_user")


class MutedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View for other users that the individual has muted.
    """

    permission_required = "profile.remove_mute"
    serializer_class = serializers.MuteduserSerializer

    def get_queryset(self):
        models.MutedUser.objects.filter(
            muter=self.request.user.gamerprofile
        ).select_related("muter", "muted_user")


class CommunityApplicationViewSet(
    PermissionRequiredMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset for a user reviewing their own applications.
    """

    permission_required = "community.view_communities"
    object_permission_required = "commuity.edit_application"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("community", "status")

    def get_queryset(self):
        return models.CommunityApplication.objects.filter(
            gamer=self.request.user.gamerprofile
        ).select_related("community")


class CommunityAdminApplicationViewSet(
    PermissionRequiredMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    View set for reviewing approving/rejecting community applications.
    """

    permission_required = "community.view_communities"
    object_permission_required = "community.destroy_application"
    serializer_class = serializers.CommunityApplicationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "community"

    def get_queryset(self):
        models.CommunityApplication.objects.filter(
            community__in=models.CommunityApplication.objects.filter(
                gamer=self.request.user.gamerprofile, community_role="admin"
            )
        ).filter(community__id=self.kwargs["community_id"]).select_related(
            "community", "gamer"
        ).filter(
            status="review"
        )

    @action(methods=["post"], detail=True)
    def approve(self, request, **kwargs):
        """
        Approve an application.
        """
        app = self.get_object()
        if not request.user.has_perm("community.approve_application", app):
            return Response(
                {"result": "You don't have permission to approve this application."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            app.approve()
        except AlreadyInCommunity:
            return Response(status=status.HTTP_200_OK)
        except CurrentlySuspended:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=["post"], detail=True)
    def reject(self, request, **kwargs):
        """
        Reject an application.
        """
        app = self.get_object()
        if not request.user.has_perm("community.approve_application", app):
            return Response(
                {"result": "You don't have permission to approve this application."},
                status=status.HTTP_403_FORBIDDEN,
            )
        app.reject()
        return Response(status=status.HTTP_202_ACCEPTED)


class SentFriendRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    A view for viewing an managing Friend Requests
    """

    serializer_class = serializers.FriendRequestSerializer

    def get_queryset(self):
        return models.GamerFriendRequest.objects.filter(
            requestor=self.request.user.gamerprofile, status="new"
        ).select_related("recipient")


class ReceivedFriendRequestViewset(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    A view for received friend requests.
    """

    serializer_class = serializers.FriendRequestSerializer

    def get_queryset(self):
        return models.GamerFriendRequest.objects.filter(
            recipient=self.request.user.gamerprofile, status="new"
        ).select_related("requestor")

    @action(methods=["put"], detail=True)
    def accept(self, request, **kwargs):
        """
        Accept a friend request.
        """
        req = self.get_object()
        req.accept()
        return Response({"result": "Accepted"}, status=status.HTTP_202_ACCEPTED)

    @action(methods=["put"], detail=True)
    def ignore(self, request, **kwargs):
        """
        Ignore a friend request.
        """
        req = self.get_object()
        req.deny()
        return Response({"result": "Ignored"}, status=status.HTTP_202_ACCEPTED)
