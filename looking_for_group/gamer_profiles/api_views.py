from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import detail_route
from rest_framework_rules.mixins import PermissionRequiredMixin
from rest_framework_rules.decorators import (
    permission_required as action_permission_required
)
from . import models, serializers
from .models import NotInCommunity, AlreadyInCommunity, CurrentlySuspended


class GamerCommunityViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    A view set of GamerCommunity functions.
    """

    permission_required = "community.list_communities"
    object_permission_required = "community.edit_community"
    queryset = models.GamerCommunity.objects.all()
    serializer_class = serializers.GamerCommunitySerializer

    @action_permission_required("community.list_communities")
    def retrieve(self, request, pk=None):
        """
        View details of the community.
        """
        return super().retrieve(request, pk)

    @detail_route(methods=["get"], permission_required='community.view_details')
    def list_members(self, request, pk=None):
        """
        List members of a community.
        """
        member_queryset = (
            models.CommunityMembership.objects.filter(community=self.get_object())
            .select_related("gamer")
            .prefetch_related("gamer__user")
        )
        page = self.paginate_queryset(member_queryset)
        if page is not None:
            member_serials = serializers.CommunityMembershipSerializer(page, many=True)
            return self.get_paginated_response(member_serials.data)
        member_serials = serializers.CommunityMembershipSerializer(
            member_queryset, many=True
        )
        return Response(member_serials.data, status=status.HTTP_200_OK)

    @detail_route(methods=["get"], permission_required='community.ban_user')
    def list_banned_users(self, request, pk=None):
        """
        Retrieve a list of banned users for this community.
        """
        ban_list = models.BannedUser.objects.filter(community=self.get_object())
        serializer = serializers.BannedUserSerializer(ban_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @detail_route(methods=["get"], permission_required='community.kick_user')
    def list_kicked_users(self, request, pk=None):
        """
        List users that have been kicked/suspended from community.
        """
        kick_list = models.KickedUser.objects.filter(community=self.get_object())
        serializer = serializers.KickedUserSerializer(kick_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @detail_route(methods=["get"], permission_required='community.view_details')
    def list_admins(self, request, pk=None):
        """
        List community admins.
        """
        admins = self.get_object().get_admins()
        serializer = serializers.GamerProfileSerializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @detail_route(methods=["get"], permission_required='community.view_details')
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
    @detail_route(methods=["post"])
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
    @detail_route(methods=["post"])
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

    permission_required = "gamer_profile.view_detail"
    serializer_class = serializers.GamerProfileSerializer
    queryset = models.GamerProfile.objects.all()

    @action_permission_required(
        "gamer_profile.view_note",
        fn=lambda request, pk: models.GamerNote.objects.filter(
            author=request.user, gamer=models.GamerProfile.objects.get(pk=pk)
        ),
    )
    @detail_route(methods=["get"])
    def view_notes(self, request, pk=None):
        notes = models.GamerNote.objects.filter(
            author=self.request.user, gamer=self.get_object().gamer
        )
        serializer = serializers.GamerNoteSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GamerNoteViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    Generic view set for gamer notes.
    """

    permission_required = "community.edit_profile_note"
    serializer_class = serializers.GamerNoteSerializer
    queryset = models.GamerNote.objects.all().select_related("author", "gamer")


class GamerRatingViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    Generic view for ratings.
    """

    permission_required = "community.view_rating"
    object_permission_required = "community.edit_rating"
    serializer_class = serializers.GamerRatingSerializer
    queryset = models.GamerRating.objects.all().select_related("rater", "gamer")


class BlockedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View for other users that the individual has blocked.
    """

    permission_required = "community.view_blocked_user"
    queryset = models.BlockedUser.objects.all().select_related(
        "blocker", "blocked_user"
    )
    serializer_class = serializers.BlockedUserSerializer


class MutedUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View for other users that the individual has muted.
    """

    permission_required = "community.view_muted_user"
    queryset = models.MutedUser.objects.all().select_related("muter", "muted_user")
    serializer_class = serializers.MuteduserSerializer


class CommunityApplicationViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    View set for community applications.
    """

    permission_required = "community.view_communities"
    object_permission_required = "community.destroy_application"
    queryset = models.CommunityApplication.objects.all().select_related(
        "community", "gamer"
    )
    serializer_class = serializers.CommunityApplicationSerializer

    @action_permission_required("community.approve_application")
    @detail_route(methods=["post"])
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
    @detail_route(methods=["post"])
    def reject(self, request, pk=None):
        """
        Reject an application.
        """
        app = self.get_object()
        app.reject()
        return Response(status=status.HTTP_202_ACCEPTED)
