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

from looking_for_group.mixins import AutoPermissionViewSetMixin, ParentObjectAutoPermissionViewSetMixin

from . import models, serializers
from .signals import player_kicked, player_left

logger = logging.getLogger("api")


class GamePostingViewSet(
    AutoPermissionViewSetMixin,
    DetailSerializerMixin,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    """
    A view set that allows the retrieval and manipulation of posted game data.
    """

    permission_classes = (IsAuthenticated,)
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
    permission_type_map = {
        **AutoPermissionViewSetMixin.permission_type_map,
        "apply": "apply",
        "leave": "leave",
    }

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

    @action(methods=["post"], detail=True)
    def apply(self, request, *args, **kwargs):
        obj = self.get_object()
        logger.debug("Retrieved game object of {}".format(obj))
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
        if request.user == obj.gm.user:
            return Response(
                data={"errors": "The GM cannot leave the game."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        player = models.Player.objects.get(gamer=request.user.gamerprofile, game=obj)
        player_left.send(models.Player, player=player)
        player.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GameSessionViewSet(
    ParentObjectAutoPermissionViewSetMixin,
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
    parent_dependent_actions = [
        "create",
        "retrieve",
        "update",
        "partial_update",
        "list",
        "destroy",
        "reschedule",
        "cancel",
        "uncancel",
        "addlog",
        "complete",
        "uncomplete",
    ]
    parent_lookup_field = "game"
    parent_object_model = models.GamePosting
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_game__slug"
    permission_type_map = {
        **ParentObjectAutoPermissionViewSetMixin.permission_type_map,
        "addlog": "view",
        "reschedule": "change",
        "cancel": "change",
        "uncancel": "change",
        "complete": "change",
        "uncomplete": "change",
    }
    permission_type_map["list"] = "view"

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
            and request.user.gamerprofile == self.get_parent_game().gm
        ):
            self.serializer_class = serializers.GameSessionGMSerializer
        return super().dispatch(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def reschedule(self, request, *args, **kwargs):
        date_serializer = serializers.ScheduleSerializer(data=request.data)
        if not date_serializer.is_valid():
            return Response(
                data=date_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        obj = self.get_object()
        if obj.status in ["complete", "cancel"]:
            return Response(
                data={
                    "errors": "This session is already marked as {} and cannot be rescheduled.".format(
                        obj.get_status_display()
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.move(date_serializer.validated_data["new_scheduled_time"])
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def complete(self, request, *args, **kwargs):
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
    def addlog(self, request, *args, **kwargs):
        """
        Create the adventure log for this session.
        """
        session = self.get_object()
        if hasattr(session, "adventurelog"):
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
    ParentObjectAutoPermissionViewSetMixin,
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
    parent_lookup_field = "session__game"
    parent_object_model = models.GamePosting
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_session__game__slug"
    serializer_class = serializers.AdventureLogSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    permission_required = "game.is_member"
    permission_type_map = {**ParentObjectAutoPermissionViewSetMixin.permission_type_map}
    permission_type_map["list"] = "add"
    parent_dependent_actions = [
        "create",
        "retrieve",
        "update",
        "partial_update",
        "destroy",
    ]

    def get_queryset(self):
        return models.AdventureLog.objects.filter(
            session__slug=self.kwargs["parent_lookup_session__slug"]
        )


class GameApplicationViewSet(
    AutoPermissionViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    View for an applicant to review, create, update, and delete their applications to games.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.GameApplicationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    permission_type_map = {**AutoPermissionViewSetMixin.permission_type_map}

    def get_queryset(self):
        logger.debug("Fetching gamerprofile from request...")
        gamer = self.request.user.gamerprofile
        logger.debug("Fetching game applications for gamer {}".format(gamer))
        qs = models.GamePostingApplication.objects.filter(
            gamer=self.request.user.gamerprofile
        ).order_by("-modified", "-created", "status")
        logger.debug(
            "Retrieved queryset of length {} for gamer {}".format(
                qs.count(), self.request.user.gamerprofile
            )
        )
        return qs


class GMGameApplicationViewSet(
    ParentObjectAutoPermissionViewSetMixin,
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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    parent_lookup_field = "game"
    parent_object_lookup_field = "slug"
    parent_object_model = models.GamePosting
    parent_object_url_kwarg = "parent_lookup_game__slug"
    parent_dependent_actions = ["list", "retrieve", "approve", "reject"]
    permission_type_map = {
        **ParentObjectAutoPermissionViewSetMixin.permission_type_map,
        "approve": "approve",
        "reject": "approve",
    }
    permission_type_map["retrieve"] = "approve"
    permission_type_map["list"] = "approve"

    def get_queryset(self):
        return models.GamePostingApplication.objects.filter(
            game__slug=self.kwargs["parent_lookup_game__slug"]
        ).exclude(status="new")

    def get_parent_game(self):
        return get_object_or_404(
            models.GamePosting, slug=self.kwargs["parent_lookup_game__slug"]
        )

    @action(methods=["post"], detail=True)
    def approve(self, request, *args, **kwargs):
        """
        Approves the game application.
        """
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
    ParentObjectAutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Provides views for players in a given game.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.PlayerSerializer
    permission_required = "game.is_member"
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    parent_lookup_field = "game"
    parent_object_model = models.GamePosting
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_game__slug"
    parent_dependent_actions = ["list", "retrieve"]
    permission_type_map = {**ParentObjectAutoPermissionViewSetMixin.permission_type_map}
    permission_type_map["list"] = "view"

    def get_parent_game(self):
        return get_object_or_404(
            models.GamePosting, slug=self.kwargs["parent_lookup_game__slug"]
        )

    def get_queryset(self):
        return models.Player.objects.filter(game=self.get_parent_game())

    @action(methods=["post"], detail=True)
    def kick(self, requests, *args, **kwargs):
        obj = self.get_object()
        player_kicked.send(request.user, player=obj)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CharacterViewSet(
    ParentObjectAutoPermissionViewSetMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    Provides views for the characters in a game.
    """

    permission_classes = (IsAuthenticated,)
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_game__slug"
    parent_lookup_field = "game"
    parent_object_model = models.GamePosting
    parent_dependent_actions = ["create", "list", "retrieve"]
    serializer_class = serializers.CharacterSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    parent_game = None
    permission_type_map = {
        **ParentObjectAutoPermissionViewSetMixin.permission_type_map,
        "approve": "approve",
        "reject": "approve",
        "deactivate": "delete",
        "reactivate": "delete",
    }
    permission_type_map["list"] = "gamelist"

    def get_parent_game(self):
        if not self.parent_game:
            self.parent_game = get_object_or_404(
                models.GamePosting, slug=self.kwargs["parent_lookup_game__slug"]
            )
        return self.parent_game

    def get_queryset(self):
        return models.Character.objects.filter(game=self.get_parent_game())

    def create(self, request, *args, **kwargs):
        if request.user.gamerprofile == self.get_parent_game().gm:
            return Response(
                data={"errors": "Only a player can create a character."},
                status=status.HTTP_403_FORBIDDEN,
            )
        char_ser = serializers.CharacterSerializer(
            data=request.data,
            context={"request": request, "game": self.get_parent_game()},
        )
        if not char_ser.is_valid():
            return Response(data=char_ser.errors, status=status.HTTP_400_BAD_REQUEST)
        char_ser.save()
        return Response(data=char_ser.data, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True)
    def approve(self, request, *args, **kwargs):
        """
        Approves the proposed character.
        """
        obj = self.get_object()
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
        obj.status = "inactive"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def reactivate(self, request, *args, **kwargs):
        """
        Reactivate an inactive character.
        """
        obj = self.get_object()
        obj.status = "pending"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class MyCharacterViewSet(
    AutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Provides a vew so that players can view all their characters in one place.
    """

    serializer_class = serializers.CharacterSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    permission_type_map = {
        **AutoPermissionViewSetMixin.permission_type_map,
        "deactivate": "delete",
        "reactivate": "delete",
    }
    permission_type_map["retrieve"] = "delete"

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

    @action(methods=["post"], detail=True)
    def reactivate(self, request, *args, **kwargs):
        """
        Reactivate an inactive character.
        """
        obj = self.get_object()
        obj.status = "pending"
        obj.save()
        return Response(
            data=self.serializer_class(obj, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
