from django.core.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_rules.mixins import PermissionRequiredMixin
from rest_framework_rules.decorators import (
    permission_required as action_permission_required
)
from . import models, serializers
from .models import NotInCommunity


class GamerCommunityViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    A view set of GamerCommunity functions.
    """

    permission_required = "community.list_communities"
    object_permission_required = "community.edit_community"
    queryset = models.GamerCommunity.objects.all()
    serializer_class = serializers.GamerCommunitySerializer

    @action_permission_required("community.view_details")
    def retrieve(self, request, pk=None):
        """
        View details of the community.
        """
        return super().retrieve(request, pk)

    @action_permission_required("community.view_details")
    @action(methods=["get"], detail=True)
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
        return Response(member_serials.data)


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
            return Response(status=403)
        except NotInCommunity:
            return Response(status=400)
        return Response(status=200)

    @action_permission_required(
        "community.ban_user",
        fn=lambda request, pk: models.CommunityMembership.objects.get(pk=pk).community,
    )
    @action(methods=["post"], detail=True)
    def ban_user(self, request, pk=None):
        try:
            reason = self.request.kwargs["reason"]
        except KeyError:
            return Response(status=400)
        banner = self.request.user.gamerprofile
        membership = self.get_object()
        try:
            membership.community.ban_user(banner, membership.gamer, reason)
        except PermissionDenied:
            return Response(status=403)
        except NotInCommunity:
            return Response(status=400)
        return Response(status=200)


class GamerProfileViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    """
    Viewset for a gamer profile.
    """

    permission_required = "gamer_profile.view_detail"
    object_permission_required = "gamer_profile.edit_profile"
    serializer_class = serializers.GamerProfileSerializer
    queryset = models.GamerProfile.objects.all()

    @action_permission_required(
        "gamer_profile.view_note",
        fn=lambda request, pk: models.GamerNote.objects.filter(
            author=request.user, gamer=models.GamerProfile.objects.get(pk=pk)
        ),
    )
    @action(methods=["get"], detail=True)
    def view_notes(self, request, pk=None):
        notes = models.GamerNote.objects.filter(
            author=self.request.user, gamer=self.get_object().gamer
        )
        serializer = serializers.GamerNoteSerializer(notes, many=True)
        return Response(serializer.data)
