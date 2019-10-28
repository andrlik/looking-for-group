import logging

from django.db import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin
from rest_framework_rules.decorators import permission_required as action_permission_required
from rest_framework_rules.mixins import PermissionRequiredMixin

from . import models, serializers

logger = logging.getLogger("api")


class GamePostingViewSet(
    PermissionRequiredMixin,
    DetailSerializerMixin,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    """
    A view set that allows the retrieval and manipulation of posted game data.
    """

    permission_required = "community.list_communities"
    object_permission_required = "game.can_view_listing"
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    serializer_class = serializers.GameDataSerializer
    serializer_detail_class = serializers.GameDataSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "published_game",
        "game_system",
        "published_module",
        "game_status",
        "game_type",
        "venue_type",
    ]

    def get_queryset(self):
        public_q = Q(privacy_level="public")
        final_q = public_q
        if self.request.user.is_authenticated:
            q_community = Q(privacy_level="community") & (
                Q(communities__in=[self.request.user.gamerprofile.communities.all()])
                | Q(gm__in=self.request.user.gamerprofile.friends.all())
            )
            gm_q = Q(gm=self.request.user.gamerprofile)
            final_q = (
                public_q
                | gm_q
                | q_community
                | Q(
                    pk__in=[
                        p.game.pk
                        for p in models.Player.objects.filter(
                            gamer=self.request.user.gamerprofile
                        )
                    ]
                )
            )
        qs = models.GamePosting.objects.filter(final_q)
        return qs

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.edit_game", self.get_object()):
            return Response(
                data={"errors": "You do not have permission to edit this game."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.edit_game", self.get_object()):
            return Response(
                data={"errors": "You do not have permission to edit this game."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("game.delete_game", self.get_object()):
            return Response(
                data={"errors": "You do not have permission to delete this game."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def apply(self, request, *args, **kwargs):
        pass

    @action(methods=["post"], detail=True)
    def join(self, request, *args, **kwargs):
        pass

    @action(methods=["post"], detail=True)
    def leave(self, request, *args, **kwargs):
        pass


class GameSessionViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Views for seeing game session data.
    """

    permission_required = "game.can_view_listing_details"
    serializer_class = serializers.GameSessionSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def check_permissions(self, request, *args, **kwargs):
        game = self.get_parent_game()
        if not request.user.has_perm("game.is_member", game):
            return Response(
                data={"errors": "Only game members can view game session details"},
                status=status.HTTP_403_FORBIDDEN,
            )

    def check_object_permissions(self, request, *args, **kwargs):
        self.check_permissions(request, *args, **kwargs)

    def get_parent_game(self):
        return get_object_or_404(
            models.GamePosting, slug=self.kwargs["parent_lookup_game__slug"]
        )

    def get_queryset(self):
        return models.GameSession.objects.filter(
            game__slug=self.kwargs["parent_lookup_game__slug"]
        )

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and self.request.user.gamerprofile == self.get_object().gm
        ):
            self.serializer_class = serializers.GameSessionGMSerializer
        return super().dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_parent_game):
            return Response(
                {"errors": "You do not have permission to edit this game session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_parent_game):
            return Response(
                {"errors": "You do not have permission to edit this game session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_parent_game):
            return Response(
                {"errors": "You do not have permission to delete this game session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def reschedule(self, request, *args, **kwargs):
        pass

    @action(methods=["post"], detail=True)
    def complete(self, request, *args, **kwargs):
        pass

    @action(methods=["post"], detail=True)
    def uncomplete(self, request, *args, **kwargs):
        pass

    @action(methods=["post"], detail=True)
    def add_log(self, request, *args, **kwargs):
        if not request.user.has_perm(
            "game.edit_create_adventure_log", self.get_parent_game()
        ):
            return Response(
                data={
                    "errors": "You do not have the necessary permissions to create a log entry for this session."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        session = self.get_object()
        if session.adventurelog:
            return Response(
                data={"errors": "This session already has an adventure log."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_serializer = serializers.AdventureLogSerializer(
            session=session, data=request.data
        )
        if not log_serializer.is_valid():
            return Response(
                data=log_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        new_log = log_serializer.save()
        return Response(
            data=serializers.AdventureLogSerializer(new_log).data,
            status=status.HTTP_201_CREATED,
        )


class AdventureLogViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Allows the manipulation of view sets.
    """

    serializer_class = serializers.AdventureLogSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    permission_required = "game.is_member"

    def check_permissions(self, request, *args, **kwargs):
        if not request.user.has_perm(self.permission_required, self.get_parent_game()):
            return Response(
                data={
                    "errors": "You don't have permission to view adventure logs for this game."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    def check_object_permissions(self, request, *args, **kwargs):
        self.check_permissions(request, *args, **kwargs)

    def get_parent_game(self):
        return get_object_or_404(
            models.GamePosting, slug=self.kwargs["parent_lookup_session__game__slug"]
        )

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm(
            "game.edit_create_adventure_log", self.get_parent_game()
        ):
            return Response(
                data={"errors": "You cannot edit this adventure log."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm(
            "game.edit_create_adventure_log", self.get_parent_game()
        ):
            return Response(
                data={"errors": "You cannot edit this adventure log."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm(
            "game.delete_adventure_log", self.get_parent_game()
        ):
            return Response(
                data={"errors": "You cannot delete this adventure log."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class GMGameApplicationViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    View for a GM to review and approve applicants.
    """

    pass
