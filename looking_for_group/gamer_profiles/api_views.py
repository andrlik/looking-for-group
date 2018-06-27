from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_rules.mixins import PermissionRequiredMixin
from rest_framework_rules.decorators import (
    permission_required as action_permission_required
)
from . import models, serializers


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
