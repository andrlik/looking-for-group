import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin
from rest_framework_rules.decorators import permission_required as action_permission_required
from rest_framework_rules.mixins import PermissionRequiredMixin

from . import models, serializers
from .models import AlreadyInCommunity, CurrentlySuspended, NotInCommunity

logger = logging.getLogger("api")


class GamerCommunityViewSet(
    PermissionRequiredMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    A view set of GamerCommunity functions.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "community.list_communities"
    queryset = models.GamerCommunity.objects.all()
    serializer_class = serializers.GamerCommunitySerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def create(self, request, *args, **kwargs):
        submitted_data = self.serializer_class(data=request.data)
        if submitted_data.is_valid():
            data_to_use = submitted_data.data
            data_to_use["owner"] = request.user.gamerprofile
            new_community = models.GamerCommunity.objects.create(**data_to_use)
            new_comm_serializer = self.serializer_class(new_community)
            return Response(
                data=new_comm_serializer.data, status=status.HTTP_201_CREATED
            )
        return Response(data=submitted_data.errors, status=status.HTTP_400_BAD_REQUEST)

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
        logger.debug(
            "Received request to update community via api by user {}".format(
                request.user
            )
        )
        logger.debug("Checking permissions...")
        if not request.user.has_perm("community.edit_community", self.get_object()):
            return Response(
                {
                    "result": "You do not have the necessary permissions to update this community."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, **kwargs)

    def partial_update(self, request, **kwargs):
        logger.debug(
            "Received request to update community via api by user {}".format(
                request.user
            )
        )
        logger.debug("Checking permissions...")
        if not request.user.has_perm("community.edit_community", self.get_object()):
            return Response(
                {
                    "result": "You do not have the necessary permissions to update this community."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, **kwargs)

    @action(
        methods=["post"], detail=True, permission_required="community.list_communities"
    )
    def join(self, request, *args, **kwargs):
        """
        If a community is not private, you can skip the application process and join directly via this method.
        """
        community = self.get_object()
        if community.private:
            return Response(
                data={
                    "errors": "You cannot join a private community. You must apply instead"
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if community in request.user.gamerprofile.communities.all():
            return Response(
                data={"errors": "You are already a member of this community."},
                status=status.HTTP_403_FORBIDDEN,
            )
        member_record = community.add_member(request.user.gamerprofile)
        member_data = serializers.CommunityMembershipSerializer(member_record)
        return Response(data=member_data.data, status=status.HTTP_201_CREATED)

    @action(
        methods=["post"], detail=True, permission_required="community.list_communities"
    )
    def leave(self, request, *args, **kwargs):
        """
        Leave the community. Must already be a member.
        """
        community = self.get_object()
        if community not in request.user.gamerprofile.communities.all():
            return Response(
                {"errors": "You aren't a member of this community."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            member = models.CommunityMembership.objects.get(
                community=community, gamer=request.user.gamerprofile
            )
            if member.gamer == community.owner:
                return Response(
                    data={
                        "errors": "You are this community's owner. You cannot leave the community unless you first transfer ownership to another community admin."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ObjectDoesNotExist:
            return Response(
                data={"errors": "You are not a member of this community."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=["post"], detail=True, permission_required="community.list_communities"
    )
    def transfer(self, request, *args, **kwargs):
        """
        Transfer ownership of the community to another community admin specified by username.
        """
        community = self.get_object()
        if not request.user.has_perm("community.transfer_ownership", community):
            return Response(
                data={
                    "errors": "Only the owner of a community can transfer ownership."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        username = request.data["username"]
        try:
            new_owner = models.GamerProfile.objects.get(username=username)
            try:
                if community.get_role(new_owner) != "Admin":
                    return Response(
                        data={
                            "errors": "The selected user is not an admin of this community and cannot be transferred ownership."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                community.owner = new_owner
                community.save()
            except models.NotInCommunity:
                return Response(
                    data={
                        "errors": "The user you specified is not a member of the community and cannot be made the owner."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ObjectDoesNotExist:
            return Response(
                data={"errors": "The username you specified does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            data=serializers.GamerCommunitySerializer(community).data,
            status=status.HTTP_200_OK,
        )

    # @action(methods=["get"], detail=True)
    # def bans(self, request, **kwargs):
    #     """
    #     Retrieve a list of banned users for this community.
    #     """
    #     community = self.get_object()
    #     if not request.user.has_perm("community.ban_user", community):
    #         return Response(
    #             {"result": "You do not have the permissions to see this data."},
    #             status=status.HTTP_403_FORBIDDEN,
    #         )
    #     ban_list = models.BannedUser.objects.filter(community=community)
    #     serializer = serializers.BannedUserSerializer(ban_list, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

    # @action(methods=["get"], detail=True)
    # def kicks(self, request, **kwargs):
    #     """
    #     List users that have been kicked/suspended from community.
    #     """
    #     community = self.get_object()
    #     if not request.user.has_perm("community.kick_user", community):
    #         return Response(
    #             {"result": "You do not have the permissions to see this data."},
    #             status=status.HTTP_403_FORBIDDEN,
    #         )
    #     kick_list = models.KickedUser.objects.filter(community=community)
    #     serializer = serializers.KickedUserSerializer(kick_list, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK)


class BannedUserViewSet(
    PermissionRequiredMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.ban_user"
    object_permission_required = "community.ban_user"
    serializer_class = serializers.BannedUserSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "community"

    def check_object_permissions(self, request, obj):
        new_obj = obj.community
        super().check_object_permissions(request, new_obj)

    def check_permissions(self, request, *args, **kwargs):
        community = get_object_or_404(
            models.GamerCommunity, slug=self.kwargs["parent_lookup_community"]
        )
        if not request.user.has_perm(self.permission_required, community):
            self.permission_denied(
                request,
                message=(
                    "You do not have permission to access or manipulate this data."
                ),
            )

    def get_queryset(self):
        return models.BannedUser.objects.filter(
            community__slug=self.kwargs["parent_lookup_community"]
        ).select_related("banner", "banned_user")


class KickedUserViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.kick_user"
    object_permission_required = "community.kick_user"
    serializer_class = serializers.KickedUserSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "community"

    def check_object_permissions(self, request, obj):
        new_obj = obj.community
        super().check_object_permissions(request, new_obj)

    def check_permissions(self, request, *args, **kwargs):
        community = get_object_or_404(
            models.GamerCommunity, slug=self.kwargs["parent_lookup_community"]
        )
        if not request.user.has_perm(self.permission_required, community):
            self.permission_denied(
                request,
                message=(
                    "You do not have permission to access or manipulate this data."
                ),
            )

    def get_queryset(self):
        logger.debug("Checking data...: {}".format(self.request.data))
        return models.KickedUser.objects.filter(
            community__slug=self.kwargs["parent_lookup_community"]
        ).select_related("kicker", "kicked_user")


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

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.view_details"
    object_permission_required = "community.view_details"
    serializer_class = serializers.CommunityMembershipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("community", "community_role")

    def check_object_permissions(self, request, obj):
        new_obj = obj.community
        super().check_object_permissions(request, new_obj)

    def check_permissions(self, request, *args, **kwargs):
        community = get_object_or_404(
            models.GamerCommunity, slug=self.kwargs["parent_lookup_community"]
        )
        if not request.user.has_perm(self.permission_required, community):
            self.permission_denied(
                request,
                message=(
                    "You do not have permission to access or manipulate this data."
                ),
            )

    def get_queryset(self):
        return (
            models.CommunityMembership.objects.filter(
                community=models.GamerCommunity.objects.get(
                    slug=self.kwargs["parent_lookup_community"]
                )
            )
            .select_related("gamer", "community")
            .order_by("community_role", "gamer__username")
        )

    @action_permission_required(
        "community.edit_gamer_role",
        fn=lambda request, parent_lookup_community, pk: models.CommunityMembership.objects.get(
            community__slug=parent_lookup_community, pk=pk
        ),
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @action_permission_required(
        "community.edit_gamer_role",
        fn=lambda request, parent_lookup_community, pk: models.CommunityMembership.objects.get(
            community__slug=parent_lookup_community, pk=pk
        ),
    )
    def partial_update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

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
            reason = self.request.data["reason"]
        except KeyError:
            return Response(status=400)
        if "end_date" in self.request.data.keys():
            end_date = self.request.data["end_date"]
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
        return Response(kick_record.data, status=status.HTTP_201_CREATED)

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
            reason = self.request.data["reason"]
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
        return Response(ban_record.data, status=status.HTTP_201_CREATED)


class GamerProfileViewSet(
    PermissionRequiredMixin,
    DetailSerializerMixin,
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
    object_permission_required = "community.list_commmunties"
    serializer_class = serializers.GamerProfileListSerializer
    serializer_detail_class = serializers.GamerProfileSerializer
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
    lookup_field = "username"
    lookup_url_kwarg = "username"

    def get_queryset(self):
        qs = models.GamerProfile.objects.exclude(
            pk__in=[
                b.blocker.pk
                for b in models.BlockedUser.objects.filter(
                    blockee=self.request.user.gamerprofile
                )
            ]
        )
        return qs

    def retrieve(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        gamer = get_object_or_404(models.GamerProfile, username=self.kwargs["username"])
        if request.user.gamerprofile.blocked_by(gamer):
            return Response(
                data={
                    "result": "You do not have the necessary rights to retrieve this user's information."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.has_perm("profile.view_detail", gamer):
            self.serializer_detail_class = serializers.GamerProfileListSerializer
        return Response(
            data=self.serializer_detail_class(gamer).data, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("profile.edit_profile", self.get_object()):
            return Response(
                {"result": "You cannot edit another user's profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("profile.edit_profile", self.get_object()):
            return Response(
                {"result": "You cannot edit another user's profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def friend(self, request, *args, **kwargs):
        target_gamer = get_object_or_404(
            models.GamerProfile, username=self.kwargs["username"]
        )
        if not request.user.has_perm("profile.can_friend", target_gamer):
            return Response(
                {"result": "You cannot send a friend request to this user."},
                status=status.HTTP_403_FORBIDDEN,
            )
        friend_req = models.GamerFriendRequest.objects.create(
            requestor=request.user.gamerprofile, recipient=target_gamer
        )
        fr_serial = serializers.FriendRequestSerializer(friend_req)
        return Response(fr_serial.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def unfriend(self, request, *args, **kwargs):
        target_gamer = get_object_or_404(
            models.GamerProfile, username=self.kwargs["username"]
        )
        if not request.user.has_perm("profile.view_detail", target_gamer):
            return Response(status=status.HTTP_403_FORBIDDEN)
        request.user.gamerprofile.friends.remove(target_gamer)
        return Response(status=status.HTTP_200_OK)

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


class GamerNoteViewSet(
    PermissionRequiredMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    Generic view set for gamer notes.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "profile.view_detail"
    object_permission_required = "profile.delete_note"
    serializer_class = serializers.GamerNoteSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "gamer"

    def check_permissions(self, request, *args, **kwargs):
        profile = get_object_or_404(
            models.GamerProfile, username=self.kwargs["parent_lookup_gamer"]
        )
        if not request.user.has_perm(self.permission_required, profile):
            self.permission_denied(
                request,
                message=(
                    "You do not have permission to access or manipulate this data."
                ),
            )

    def create(self, request, *args, **kwargs):
        new_note_serializer = self.serializer_class(data=request.data)
        if new_note_serializer.is_valid():
            data_to_use = new_note_serializer.validated_data
            data_to_use["gamer"] = get_object_or_404(
                models.GamerProfile, username=self.kwargs["parent_lookup_gamer"]
            )
            data_to_use["author"] = request.user.gamerprofile
            try:
                new_note = models.GamerNote.objects.create(**data_to_use)
            except IntegrityError as ie:
                logger.error(
                    "Error when trying to create gamer note from serializer. Message was {}".format(
                        str(ie)
                    )
                )
                return Response(
                    data={
                        "error": "Something went wrong when creating this record. This error has been logged. If you continue to receive this error, please report this at https://app.lfg.directory/helpdesk/issues/"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(
                data=self.serializer_class(new_note).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            data=new_note_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    def get_queryset(self):
        return (
            models.GamerNote.objects.filter(
                gamer=models.GamerProfile.objects.get(
                    username=self.kwargs["parent_lookup_gamer"]
                )
            )
            .filter(author=self.request.user.gamerprofile)
            .select_related("author", "gamer", "gamer__user")
            .order_by("-created")
        )


class BlockedUserViewSet(
    PermissionRequiredMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    View for other users that the individual has blocked.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "community.destroy_block"
    serializer_class = serializers.BlockedUserSerializer

    def get_queryset(self):
        return models.BlockedUser.objects.filter(
            blocker=self.request.user.gamerprofile
        ).select_related("blocker", "blockee")


class MutedUserViewSet(
    PermissionRequiredMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    View for other users that the individual has muted.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "profile.remove_mute"
    serializer_class = serializers.MuteduserSerializer

    def get_queryset(self):
        return models.MutedUser.objects.filter(
            muter=self.request.user.gamerprofile
        ).select_related("muter", "mutee")


class CommunityApplicationViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset for a user reviewing their own applications.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    serializer_class = serializers.CommunityApplicationSerializer
    object_permission_required = "community.edit_application"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("community", "status")

    def get_queryset(self):
        return models.CommunityApplication.objects.filter(
            gamer=self.request.user.gamerprofile
        ).select_related("community")


class CommunityAdminApplicationViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    View set for reviewing approving/rejecting community applications.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "community.approve_application"
    serializer_class = serializers.CommunityApplicationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["community"]

    def check_permissions(self, request, *args, **kwargs):
        community = get_object_or_404(
            models.GamerCommunity, slug=self.kwargs["parent_lookup_community"]
        )
        if not request.user.has_perm("community.edit_roles", community):
            self.permission_denied(
                request, message="You do not have permission to run this query."
            )

    def get_queryset(self):
        return (
            models.CommunityApplication.objects.filter(
                community__in=[
                    m.community
                    for m in models.CommunityMembership.objects.filter(
                        gamer=self.request.user.gamerprofile, community_role="admin"
                    )
                ]
            )
            .select_related("community", "gamer")
            .filter(status="review")
        )

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset()).filter(
            community__slug=self.kwargs["parent_lookup_community"]
        )

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    @action(methods=["post"], detail=True)
    def approve(self, request, *args, **kwargs):
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
            app.approve_application()
        except AlreadyInCommunity:
            return Response(status=status.HTTP_200_OK)
        except CurrentlySuspended:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=["post"], detail=True)
    def reject(self, request, *args, **kwargs):
        """
        Reject an application.
        """
        app = self.get_object()
        if not request.user.has_perm("community.approve_application", app):
            return Response(
                {"result": "You don't have permission to approve this application."},
                status=status.HTTP_403_FORBIDDEN,
            )
        app.reject_application()
        return Response(status=status.HTTP_202_ACCEPTED)


class SentFriendRequestViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    A view for viewing an managing Friend Requests
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "profile.withdraw_friend_request"
    serializer_class = serializers.FriendRequestSerializer

    def get_queryset(self):
        return models.GamerFriendRequest.objects.filter(
            requestor=self.request.user.gamerprofile, status="new"
        ).select_related("recipient")


class ReceivedFriendRequestViewset(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    A view for received friend requests.
    """

    permission_required = "community.list_communities"
    object_permission_required = "profile.approve_friend_request"
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.FriendRequestSerializer

    def get_queryset(self):
        return models.GamerFriendRequest.objects.filter(
            recipient=self.request.user.gamerprofile, status="new"
        ).select_related("requestor")

    @action(methods=["post"], detail=True)
    def accept(self, request, *args, **kwargs):
        """
        Accept a friend request.
        """
        req = self.get_object()
        req.accept()
        return Response({"result": "Accepted"}, status=status.HTTP_202_ACCEPTED)

    @action(methods=["post"], detail=True)
    def ignore(self, request, *args, **kwargs):
        """
        Ignore a friend request.
        """
        req = self.get_object()
        req.deny()
        return Response({"result": "Ignored"}, status=status.HTTP_202_ACCEPTED)
