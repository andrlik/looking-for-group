import logging

from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.openapi import Parameter
from drf_yasg.utils import no_body, swagger_auto_schema
from notifications.signals import notify
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.decorators import parser_classes as dparser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from looking_for_group.mixins import AutoPermissionViewSetMixin, ParentObjectAutoPermissionViewSetMixin

from . import models, serializers
from .signals import player_kicked, player_left

logger = logging.getLogger("api")

parent_lookup_game__slug = Parameter(
    name="parent_lookup_game__slug",
    in_="path",
    type="string",
    format=openapi.FORMAT_SLUG,
    description="Slug of related game object.",
)
parent_lookup_session__slug = Parameter(
    name="parent_lookup_session__slug",
    in_="path",
    type="string",
    format=openapi.FORMAT_SLUG,
    description="Slug of related session object.",
)
parent_lookup_session__game__slug = Parameter(
    name="parent_lookup_session__game__slug",
    in_="path",
    type="string",
    format=openapi.FORMAT_SLUG,
    description="Slug of related game object.",
)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Games",
        operation_description="Fetch a list of game records. **NOTE**: You will probably want to filter by status at least.",
    ),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_summary="Game: Create",
        operation_description="Create a new game posting.",
        request_body=serializers.GameDataSerializer,
        responses={201: serializers.GameDataSerializer},
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Game: Details",
        operation_description="Fetch the details for the given game. **NOTE**: If you are not a member of the game, only a subset of the available information will be displayed.",
        responses={
            200: serializers.GameDataSerializer,
            403: "You are not authorized to view this game.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Game: Update",
        operation_description="Update the details of this game. (Only available to GM)",
        request_body=serializers.GameDataSerializer,
        responses={
            200: serializers.GameDataSerializer,
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Game: Update",
        operation_description="Update the details of this game. (Only available to GM)",
        request_body=serializers.GameDataSerializer,
        responses={
            200: serializers.GameDataSerializer,
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Game: Delete",
        operation_description="Delete the given game. (Only available to GM.)",
        request_body=no_body,
        responses={204: "Game was deleted.", 403: "You are not the GM of this game."},
    ),
)
@method_decorator(
    name="leave",
    decorator=swagger_auto_schema(
        operation_summary="Game: Leave",
        operation_description="Leave the current game. (Players only.)",
        request_body=no_body,
        reponses={
            204: "You have successfully left the game.",
            400: "You are not a member of this game.",
            403: "You are the GM and cannot leave.",
        },
    ),
)
@method_decorator(
    name="apply",
    decorator=swagger_auto_schema(
        operation_summary="Game: Apply",
        operation_description="Apply to join this game.",
        request_body=serializers.GameApplicationSerializer,
        responses={
            201: serializers.GameApplicationSerializer,
            400: "You are already a member of this game.",
            403: "You are not permitted to apply to this game either due to your access rights or the game's status.",
        },
    ),
)
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
    parser_classes = [FormParser, MultiPartParser]
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Game: List Sessions",
        operation_description="List the sessions for the given game.",
        manual_parameters=[parent_lookup_game__slug],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Details",
        operation_description="Get the details for the given session. **NOTE**: If the user is just a player, the GM notes and player details will not be included.",
        manual_parameters=[parent_lookup_game__slug],
        responses={
            200: serializers.GameSessionGMSerializer,
            403: "You are not a member of this game.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Update",
        operation_description="Update details of the game session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.GameSessionGMSerializer,
        responses={
            200: serializers.GameSessionGMSerializer,
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Update",
        operation_description="Update details of the game session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.GameSessionGMSerializer,
        responses={
            200: serializers.GameSessionGMSerializer,
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Delete",
        operation_description="Delete the game session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.GameSessionGMSerializer,
        responses={
            204: "Session was deleted.",
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="cancel",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Cancel",
        operation_description="Cancel the game session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.GameSessionGMSerializer,
            400: "This session is already canceled or complete.",
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="uncancel",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Uncancel",
        operation_description="Uncancel the game session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.GameSessionGMSerializer,
            400: "This session is not canceled.",
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="complete",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Mark Complete",
        operation_description="Mark the game session as complete.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.GameSessionGMSerializer,
            400: "This session is already canceled or complete.",
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="uncomplete",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Uncomplete",
        operation_description="Undo the completion status of the session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.GameSessionGMSerializer,
            400: "This session isn't marked as complete.",
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="reschedule",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Reschedule",
        operation_description="Reschedule the game session to another date/time.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.ScheduleSerializer,
        responses={
            200: serializers.GameSessionGMSerializer,
            400: "Your date and time were invalid or the session is already marked as complete or canceled.",
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="addlog",
    decorator=swagger_auto_schema(
        operation_summary="Game Session: Add Adventure Log",
        operation_description="Add an adventure log to this session.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.AdventureLogSerializer,
        responses={
            201: serializers.AdventureLogSerializer,
            400: "This session already has an adventure log. You should update that instead.",
            403: "You don't have permission to add an adventure log.",
        },
    ),
)
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


@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Adventure Log: Details",
        operation_description="Fetch the details for a given adventure log.",
        manual_parameters=[
            parent_lookup_session__game__slug,
            parent_lookup_session__slug,
        ],
        responses={
            200: serializers.AdventureLogSerializer,
            403: "You are not a member of this game.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Adventure Log: Update",
        operation_description="Update the details for a given adventure log.",
        manual_parameters=[
            parent_lookup_session__game__slug,
            parent_lookup_session__slug,
        ],
        request_body=serializers.AdventureLogSerializer,
        responses={
            200: serializers.AdventureLogSerializer,
            403: "You don't have permissions to edit this adventure log.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Adventure Log: Update",
        operation_description="Update the details for a given adventure log.",
        manual_parameters=[
            parent_lookup_session__game__slug,
            parent_lookup_session__slug,
        ],
        request_body=serializers.AdventureLogSerializer,
        responses={
            200: serializers.AdventureLogSerializer,
            403: "You don't have permissions to edit this adventure log.",
        },
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Adventure Log: Delete",
        operation_description="Delete a given adventure log.",
        manual_parameters=[
            parent_lookup_session__game__slug,
            parent_lookup_session__slug,
        ],
        request_body=no_body,
        responses={
            204: "The adventure log was successfully deleted.",
            403: "You don't have permissions to edit this adventure log.",
        },
    ),
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Your Game Applications",
        operation_description="Fetch a list of all your game applications.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Your Game Application: Details",
        operation_description="Fetch the details of your game application.",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Your Game Application: Update",
        operation_description="Update the details of your game application.",
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Your Game Application: Update",
        operation_description="Update the details of your game application.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Your Game Application: Withdraw",
        operation_description="Withdraw your game application by deleting the record.",
    ),
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Applicants for Game",
        operation_description="List the applicants for the current game. (GM Only)",
        manual_parameters=[parent_lookup_game__slug],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Game Applicant: Details",
        operation_description="Fetch details for a given game application. (GM Only)",
        manual_parameters=[parent_lookup_game__slug],
        reponses={
            200: serializers.GameApplicationGMSerializer,
            403: "You are not the GM for this game.",
        },
    ),
)
@method_decorator(
    name="approve",
    decorator=swagger_auto_schema(
        operation_summary="Game Applicant: Approve",
        operation_description="Approve the game applicant and add as a player to game.",
        request_body=no_body,
        responses={
            201: serializers.PlayerSerializer,
            403: "You are not the GM of this game.",
        },
    ),
)
@method_decorator(
    name="reject",
    decorator=swagger_auto_schema(
        operation_summary="Game Applicant: Reject",
        operation_description="Reject the game applicant.",
        request_body=no_body,
        responses={
            200: serializers.GameApplicationGMSerializer,
            403: "You are not the GM of this game.",
        },
    ),
)
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Game: Player List",
        operation_description="List players for a given game",
        manual_parameters=[parent_lookup_game__slug],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Player: Details",
        operation_description="Details for a player record in a given game.",
        manual_parameters=[parent_lookup_game__slug],
        responses={
            200: serializers.PlayerSerializer,
            403: "You are not a member of this game.",
        },
    ),
)
@method_decorator(
    name="kick",
    decorator=swagger_auto_schema(
        operation_summary="Player: Kick from game",
        operation_description="Kick the player out of the game.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            204: "Player was removed from the game.",
            403: "You are not the GM of this game.",
        },
    ),
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
    def kick(self, request, *args, **kwargs):
        obj = self.get_object()
        player_kicked.send(request.user, player=obj)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Game: List Characters",
        operation_description="Fetch the list of characters for a given game.",
        manual_parameters=[parent_lookup_game__slug],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Game: Character Details",
        operation_description="Fetch the details of a character for a given game.",
        manual_parameters=[parent_lookup_game__slug],
        responses={
            200: serializers.CharacterSerializer,
            403: "You are not a member of this game.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Game: Update Character Details",
        operation_description="Update the character for the given game.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.CharacterSerializer,
        responses={
            200: serializers.CharacterSerializer,
            403: "You are not the owner of this character or the GM of the game.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Game: Update Character Details",
        operation_description="Update the character for the given game.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=serializers.CharacterSerializer,
        responses={
            200: serializers.CharacterSerializer,
            403: "You are not the owner of this character or the GM of the game.",
        },
    ),
)
@method_decorator(
    name="deactivate",
    decorator=swagger_auto_schema(
        operation_summary="Game: Deactivate Character",
        operation_description="Mark the character as inactive.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.CharacterSerializer,
            400: "This character is already inactive.",
            403: "You are not the owner of this character or the GM of the game.",
        },
    ),
)
@method_decorator(
    name="reactivate",
    decorator=swagger_auto_schema(
        operation_summary="Game: Reactivate Character",
        operation_description="Mark the character as active.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.CharacterSerializer,
            400: "This character is already active.",
            403: "You are not the owner of this character or the GM of the game.",
        },
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Game: Delete Character",
        operation_description="Delete the character.",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            204: "Character was deleted.",
            403: "You are not the owner of this character.",
        },
    ),
)
@method_decorator(
    name="approve",
    decorator=swagger_auto_schema(
        operation_summary="Game: Approve Character",
        operation_description="Mark the character as approved (GM Only).",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.CharacterSerializer,
            400: "This character is already approved.",
            403: "You are not the GM of the game.",
        },
    ),
)
@method_decorator(
    name="reject",
    decorator=swagger_auto_schema(
        operation_summary="Game: Reject Character",
        operation_description="Mark the character as rejected (GM Only).",
        manual_parameters=[parent_lookup_game__slug],
        request_body=no_body,
        responses={
            200: serializers.CharacterSerializer,
            400: "This character is already rejected.",
            403: "You are not the GM of the game.",
        },
    ),
)
class CharacterViewSet(
    ParentObjectAutoPermissionViewSetMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    Provides views for the characters in a game.
    """

    permission_classes = (IsAuthenticated,)
    parser_classes = [FormParser, MultiPartParser]
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Your Characters",
        operation_description="Fetch a list of all of your characters.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Your Character: Details",
        operation_description="Fetch the details of your character.",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Your Character: Update",
        operation_description="Update the details of your character.",
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Your Character: Update",
        operation_description="Update the details of your character.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Your Character: Delete",
        operation_description="Delete your character.",
        request_body=no_body,
        responses={204: "Character was deleted."},
    ),
)
@method_decorator(
    name="deactivate",
    decorator=swagger_auto_schema(
        operation_summary="Your Character: Deactivate",
        operation_description="Mark your character as inactive.",
        request_body=no_body,
        responses={
            200: "Character was marked as inactive.",
            400: "Character was already inactive.",
        },
    ),
)
@method_decorator(
    name="reactivate",
    decorator=swagger_auto_schema(
        operation_summary="Your Character: Reactivate",
        operation_description="Mark your character as active.",
        request_body=no_body,
        responses={
            200: "Character was marked as active.",
            400: "Character was already active.",
        },
    ),
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
    parser_classes = [FormParser, MultiPartParser]

    def get_queryset(self):
        return models.Character.objects.filter(
            player__gamer=self.request.user.gamerprofile
        )

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @dparser_classes([FormParser, JSONParser])
    def destroy(self, request, *args, **kwargs):
        self.parser_classes = [FormParser, JSONParser]
        return super().destroy(request, *args, **kwargs)
