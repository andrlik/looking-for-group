from django.core.exceptions import PermissionDenied
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_rules.decorators import permission_required as action_permission_required
from rest_framework_rules.mixins import PermissionRequiredMixin

from . import models, serializers
from .models import AlreadyInCommunity, CurrentlySuspended, NotInCommunity


class GamerCommunityViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    A view set of GamerCommunity functions.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "community.view_details"
    queryset = models.GamerCommunity.objects.all()
    serializer_class = serializers.GamerCommunitySerializer

    @action(methods=["post"], permission_required="community.apply")
    def apply(self, request, pk=None):
        """
        Apply to this community.
        """
        message = None
        if "message" in request.data.keys():
            message = request.data["message"]
        application = models.CommunityApplication.objects.create(
            gamer=request.user.gamerprofile,
            community=self.get_object(),
            message=message,
            status="review",
        )
        return status.HTTP_201_CREATED

    @action_permission_required("community.delete_community")
    def destroy(self, request, pk=None):
        """
        Destroy the community.
        """
        return super().destroy(request, pk)

    @action_permission_required("community.edit_community")
    def update(self, request, pk=None):
        return super().update(request, pk)

    @action_permission_required("community.edit_community")
    def partial_update(self, request, pk=None):
        return super().partial_update(request, pk)

    @action(methods=["get"], detail=True, permission_required="community.view_details")
    def list_members(self, request, pk=None):
        """
        List members of a community.
        """
        member_queryset = (
            models.CommunityMembership.objects.filter(community=self.get_object())
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

    @action(methods=["get"], detail=True, permission_required="community.ban_user")
    def list_banned_users(self, request, pk=None):
        """
        Retrieve a list of banned users for this community.
        """
        ban_list = models.BannedUser.objects.filter(community=self.get_object())
        serializer = serializers.BannedUserSerializer(ban_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, permission_required="community.kick_user")
    def list_kicked_users(self, request, pk=None):
        """
        List users that have been kicked/suspended from community.
        """
        kick_list = models.KickedUser.objects.filter(community=self.get_object())
        serializer = serializers.KickedUserSerializer(kick_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, permission_required="community.view_details")
    def list_admins(self, request, pk=None):
        """
        List community admins.
        """
        admins = self.get_object().get_admins()
        serializer = serializers.GamerProfileSerializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, permission_required="community.view_details")
    def list_mods(self, request, pk=None):
        """
        List community moderators.
        """
        mods = self.get_object().get_moderators()
        serializer = serializers.GamerProfileSerializer(mods)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommunityMembershipViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    A viewset for Community membership.
    """

    permission_required = "community.view_roles"
    object_permission_required = "community.edit_membership"
    queryset = models.CommunityMembership.objects.all()
    serializer_class = serializers.CommunityMembershipSerializer

    @action_permission_required(
        "community.kick_user",
        fn=lambda request, pk: models.CommunityMembership.objects.get(pk=pk).community,
    )
    @action(methods=["post"], detail=True)
    def kick_user(self, request, pk=None):
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
            membership.community.kick_user(
                kicker, membership.gamer, reason, earliest_reapply=end_date
            )
        except PermissionDenied:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        except NotInCommunity:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action_permission_required(
        "community.ban_user",
        fn=lambda request, pk: models.CommunityMembership.objects.get(pk=pk).community,
    )
    @action(methods=["post"], detail=True)
    def ban_user(self, request, pk=None):
        try:
            reason = self.request.kwargs["reason"]
        except KeyError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        banner = self.request.user.gamerprofile
        membership = self.get_object()
        try:
            membership.community.ban_user(banner, membership.gamer, reason)
        except PermissionDenied:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        except NotInCommunity:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)


class GamerProfileViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    Viewset for a gamer profile.
    """

    permission_classes = (permissions.IsAuthenticated,)
    permission_required = "community.list_communities"
    object_permission_required = "profile.view_detail"
    serializer_class = serializers.GamerProfileSerializer
    # queryset = models.GamerProfile.objects.all().select_related("user").prefetch_related("friends")

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
        qs_combined = qs.union(qs_community)
        qs_remove_blocked = combined_qs.exclude(
            id__in=[
                b.blocker.id
                for b in models.BlockedUser.objects.filter(
                    blockee=request.user.gamerprofile
                )
            ]
        )
        return qs_remove_blocked

    # @action_permission_required(
    #     "profile.view_note",
    #     fn=lambda request, pk: models.GamerNote.objects.filter(
    #         author=request.user, gamer=models.GamerProfile.objects.get(pk=pk)
    #     ),
    # )
    # @action(methods=["get"], detail=True)
    # def view_notes(self, request, pk=None):
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

    def get_queryset(self):
        return models.GamerNote.objects.filter(
            author=self.request.user.gamerprofile
        ).select_related("author", "gamer", "gamer__user")


class BlockedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View for other users that the individual has blocked.
    """

    permission_required = "community.view_blocked_user"
    serializer_class = serializers.BlockedUserSerializer

    def get_queryset(self):
        models.BlockedUser.objects.filter(
            blocker=self.request.user.gamerprofile
        ).select_related("blocker", "blocked_user")


class MutedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View for other users that the individual has muted.
    """

    permission_required = "community.view_muted_user"
    serializer_class = serializers.MuteduserSerializer

    def get_queryset(self):
        models.MutedUser.objects.filter(
            muter=self.request.user.gamerprofile
        ).select_related("muter", "muted_user")


class CommunityApplicationViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    Viewset for a user reviewing their own applications.
    """

    permission_required = "community.view_communities"
    object_permission_required = "commuity.edit_application"

    def get_queryset(self):
        return models.CommunityApplication.objects.filter(
            gamer=self.request.user.gamerprofile
        ).select_related("community")

    @action_permission_required("community.apply")
    def create(self, request, *args, **kwargs):
        """
        Not permitted in this view set. Use the community apply action instead.
        """
        return Response(status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        """
        Not allowed. You need to withdraw the application and resumbit if you want to change something.
        """
        return Response(status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        """
        Not allowed. You need to withdraw the application and resumbit if you want to change something.
        """
        return Response(status.HTTP_403_FORBIDDEN)


class CommunityAdminApplicationViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View set for reviewing approving/rejecting community applications.
    """

    permission_required = "community.view_communities"
    object_permission_required = "community.destroy_application"
    serializer_class = serializers.CommunityApplicationSerializer

    def get_queryset(self):
        models.CommunityApplication.objects.filter(
            community__in=models.CommunityApplication.objects.filter(
                gamer=self.request.user.gamerprofile,
                community_role="admin",
                status="review",
            )
        ).select_related("community", "gamer")

    @action_permission_required("community.approve_application")
    @action(methods=["post"], detail=True)
    def approve(self, request, pk=None):
        """
        Approve an application.
        """
        app = self.get_object()
        try:
            app.approve()
        except AlreadyInCommunity:
            return Response(status=status.HTTP_200_OK)
        except CurrentlySuspended:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)

    @action_permission_required("community.approve_application")
    @action(methods=["post"], detail=True)
    def reject(self, request, pk=None):
        """
        Reject an application.
        """
        app = self.get_object()
        app.reject()
        return Response(status=status.HTTP_202_ACCEPTED)
