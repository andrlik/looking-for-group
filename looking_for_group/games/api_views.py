import logging

from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from notifications.signals import notify
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin
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
    model = models.GamePosting
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    serializer_class = serializers.GameDataListSerializer
    serializer_detail_class = serializers.GameDataSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "published_game",
        "game_system",
        "published_module",
        "status",
        "game_type",
        "game_mode",
    ]

    def get_queryset(self):
        gamer = self.request.user.gamerprofile
        friends = gamer.friends.all()
        communities = [f.id for f in gamer.communities.all()]
        game_player_ids = [
            obj.game.id
            for obj in models.Player.objects.filter(gamer=gamer).select_related("game")
        ]
        q_gm = Q(gm=gamer)
        q_gm_is_friend = Q(gm__in=friends) & Q(privacy_level="community")
        q_isplayer = Q(id__in=game_player_ids)
        q_community = Q(communities__id__in=communities) & Q(privacy_level="community")
        q_public = Q(privacy_level="public")
        qs = models.GamePosting.objects.filter(
            q_gm | q_public | q_gm_is_friend | q_isplayer | q_community
        ).distinct()
        return qs

    def create(self, request, *args, **kwargs):
        self.serializer_class = serializers.GameDataSerializer
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not request.user.has_perm("game.is_member", self.get_object()):
            logger.debug(
                "User is not a member of game, swtiching serializer to list view mode."
            )
            self.serializer_detail_class = serializers.GameDataListSerializer
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_object()):
            return Response(
                data={"errors": "You do not have permission to edit this game."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_object()):
            return Response(
                data={"errors": "You do not have permission to edit this game."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_object()):
            return Response(
                data={"errors": "You do not have permission to delete this game."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def apply(self, request, *args, **kwargs):
        obj = self.get_object()
        logger.debug("Retrieved game object of {}".format(obj))
        if not request.user.is_authenticated or not request.user.has_perm(
            "game.can_apply", obj
        ):
            return Response(
                data={
                    "errors": "Either this game is not open to new players or you don't have the necessary permissions to apply to this game."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.has_perm("game.is_member", obj):
            return Response(
                data={"errors": "You are already in this game..."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_application = serializers.GameApplicationSerializer(
            data=request.data, context={"request": request}
        )
        if not new_application.is_valid():
            return Response(
                data=new_application.errors, status=status.HTTP_400_BAD_REQUEST
            )
        app = models.GamePostingApplication.objects.create(
            game=obj,
            gamer=request.user.gamerprofile,
            message=new_application.validated_data["message"],
            status="pending",
        )
        notify.send(
            request.user.gamerprofile,
            recipient=obj.gm.user,
            verb="submitted application",
            action_object=app,
            target=obj,
        )
        return Response(
            data=serializers.GameApplicationSerializer(
                app, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=["post"], detail=True)
    def leave(self, request, *args, **kwargs):
        obj = self.get_object()
        if not request.user.is_authenticated or not request.user.has_perm(
            "game.is_member", obj
        ):
            return Response(
                data={
                    "errors": "You can't leave a game if you are not already a member."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user == obj.gm.user:
            return Response(
                data={"errors": "The GM cannot leave the game."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        player = models.Player.objects.get(gamer=request.user.gamerprofile, game=obj)
        player.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    model = models.GameSession
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
        return self.model.objects.filter(
            game__slug=self.kwargs["parent_lookup_game__slug"]
        ).order_by("-scheduled_time")

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and self.request.user.gamerprofile == self.get_object().gm
        ):
            self.serializer_class = serializers.GameSessionGMSerializer
        return super().dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_parent_game()):
            return Response(
                {"errors": "You do not have permission to edit this game session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_parent_game()):
            return Response(
                {"errors": "You do not have permission to edit this game session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_edit_listing", self.get_parent_game()):
            return Response(
                {"errors": "You do not have permission to delete this game session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def reschedule(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_schedule", self.get_parent_game()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to reschedule this session."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        date_serializer = serializers.ScheduleSerializer(data=request.data)
        if not date_serializer.is_valid():
            return Response(
                data={
                    "new_scheduled_time": "You specified the datetime in an invalid format."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj = self.get_object()
        obj.move(date_serializer.validated_data["new_scheduled_time"])
        return Response(
            data=self.serializer_class(obj, context={"request": request}),
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def complete(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_schedule", self.get_parent_game()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to complete this session."
                }
            )
        obj = self.get_object()
        if obj.status in ["complete", "cancel"]:
            return Response(
                data={
                    "errors": "This object is either already completed or canceled and cannot be toggled to complete."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.status = "complete"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def uncomplete(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_schedule", self.get_parent_game()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to uncomplete this session."
                }
            )
        obj = self.get_object()
        if obj.status != "complete":
            return Response(
                data={
                    "errors": "This object is not completed and so completion cannot be undone."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.status = "pending"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def cancel(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_schedule", self.get_parent_game()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to cancel this session."
                }
            )
        obj = self.get_object()
        if obj.status in ["complete", "cancel"]:
            return Response(
                data={"errors": "This session is already completed or canceled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.cancel()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def uncancel(self, request, *args, **kwargs):
        if not request.user.has_perm("game.can_schedule", self.get_parent_game()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to uncancel this session."
                }
            )
        obj = self.get_object()
        if obj.status != "cancel":
            return Response(
                data={
                    "errors": "This session is not canceled and can't be changed this way."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.uncancel()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def add_log(self, request, *args, **kwargs):
        """
        Create the adventure log for this session.
        """
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
            session=session, data=request.data, context={"request": request}
        )
        if not log_serializer.is_valid():
            return Response(
                data=log_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        new_log = log_serializer.save()
        return Response(
            data=serializers.AdventureLogSerializer(
                new_log, context={"request": request}
            ).data,
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

    model = models.AdventureLog
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


class GameApplicationViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    View for an applicant to review, create, update, and delete their applications to games.
    """

    serializer_class = serializers.GameApplicationSerializer
    permission_required = "community.list_communities"
    object_permission_required = "game.can_edit_application"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return models.GamePostingApplication.objects.filter(
            gamer=self.request.user.gamerprofile
        )


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

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.GameApplicationGMSerializer
    permission_required = "game.can_edit_listing"
    object_permission_required = "game.can_edit_listing"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return models.GamePostingApplication.objects.filter(
            game__slug=self.kwargs["parent_lookup_game__slug"]
        ).exclude(status="new")

    def get_parent_game(self):
        return get_object_or_404(
            models.GamePosting, slug=self.kwargs["parent_lookup_game__slug"]
        )

    def check_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_perm(
            self.permission_required, self.get_parent_game()
        ):
            logger.debug("Permission missing!")
            self.permission_denied(
                request,
                message="You don't have permission to administrate applications to this game.",
            )

    def check_object_permissions(self, request, *args, **kwargs):
        self.check_permissions(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def approve(self, request, *args, **kwargs):
        """
        Approves the game application.
        """
        self.check_permissions(request, *args, **kwargs)
        obj = self.get_object()
        obj.status = "approve"
        player = models.Player.objects.create(game=obj.game, gamer=obj.gamer)
        obj.save()
        return Response(
            data=serializers.PlayerSerializer(
                player, context={"request", request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=["post"], detail=True)
    def reject(self, request, *args, **kwargs):
        """
        Rejects the game application.
        """
        self.check_permissions(request, *args, **kwargs)
        obj = self.get_object()
        obj.status = "deny"
        obj.save()
        notify.send(
            obj,
            recipient=obj.gamer.user,
            verb="Your player application was not accepted",
            action_object=obj,
            target=obj.game,
        )
        return Response(
            data=serializers.GameApplicationSerializer(
                obj, context={"request": request}
            ).data,
            status=status.HTTP_200_OK,
        )


class PlayerViewSet(
    PermissionRequiredMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Provides views for players in a given game.
    """

    serializer_class = serializers.PlayerSerializer
    permission_required = "game.is_member"
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_parent_game(self):
        return get_object_or_404(
            models.GamePosting, slug=self.kwargs["parent_lookup_game__slug"]
        )

    def check_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_perm(
            self.permission_required, self.get_parent_game()
        ):
            return Response(
                data={
                    "errors": "You don't have the required permissions to view players in this game."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    def check_object_permissions(self, request, *args, **kwargs):
        self.check_permissions(request, *args, **kwargs)

    def get_queryset(self):
        return models.Player.objects.filter(game=self.get_parent_game())


class CharacterViewSet(
    PermissionRequiredMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    Provides views for the characters in a game.
    """

    serializer_class = serializers.CharacterSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    permission_required = "game.is_member"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_parent_game(self):
        return models.GamePosting.objects.get(
            slug=self.kwargs["parent_lookup_player__game__slug"]
        )

    def get_queryset(self):
        return models.Character.objects.filter(game=self.get_parent_game())

    def check_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_perm(
            self.permission_required, self.get_parent_game()
        ):
            return Response(
                data={
                    "errors": "You don't have the permissions required to view this character's information."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    def check_object_permissions(self, request, *args, **kwargs):
        self.check_permissions(self, request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def approve(self, request, *args, **kwargs):
        """
        Approves the proposed character.
        """
        obj = self.get_object()
        if not request.user.has_perm("game.approve_character", obj):
            return Response(
                data={
                    "errors": "You don't have the permissions required to approve a character."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        obj.status = "approved"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def reject(self, request, *args, **kwargs):
        """
        Rejects the proposed character.
        """
        obj = self.get_object()
        if not request.user.has_perm("game.approve_character", obj):
            return Response(
                data={
                    "errors": "You don't have the permissions required to reject this character."
                }
            )
        obj.status = "rejected"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def deactivate(self, request, *args, **kwargs):
        """
        Make a character inactive.
        """
        obj = self.get_object()
        if not request.user.has_perm("game.is_character_editor", obj):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to edit this character."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        obj.status = "inactive"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.is_character_editor", self.get_object()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to edit this character."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.has_perm("game.is_character_editor", self.get_object()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to edit this character."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("game.is_character_editor", self.get_object()):
            return Response(
                data={
                    "errors": "You don't have the necessary permissions to edit this character."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        super().destroy(request, *args, **kwargs)


class MyCharacterViewSet(
    PermissionRequiredMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    Provides a vew so that players can view all their characters in one place.
    """

    serializer_class = serializers.CharacterSerializer
    permission_required = "community.list_communities"
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        return models.Character.objects.filter(
            player__gamer=self.request.user.gamerprofile
        )

    @action(methods=["post"], detail=True)
    def deactivate(self, request, *args, **kwargs):
        """
        Make a character inactive.
        """
        obj = self.get_object()
        obj.status = "inactive"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
