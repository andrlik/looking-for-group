import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.openapi import TYPE_STRING, Parameter, Schema
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, parser_classes
from rest_framework.parsers import FileUploadParser, FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from looking_for_group.mixins import AutoPermissionViewSetMixin, ParentObjectAutoPermissionViewSetMixin

from .. import models, serializers
from ..models import AlreadyInCommunity, CurrentlySuspended, NotInCommunity
from ..rules import is_membership_subject

logger = logging.getLogger("api")

parent_lookup_community = Parameter(
    name="parent_lookup_community",
    in_="path",
    type="string",
    format=openapi.FORMAT_SLUG,
    description="Slug of related community.",
)
parent_lookup_profile = Parameter(
    name="parent_lookup_gamer",
    in_="path",
    type="string",
    format=openapi.FORMAT_SLUG,
    description="Username of related user.",
)

ban_reason_schema = Schema(
    title="Ban submission",
    type="object",
    description="Simple object to send for banning a user from a community.",
    properties={"reason": {"type": TYPE_STRING, "required": True}},
    required=["reason"],
)

kick_reason_schema = Schema(
    title="Kick submission",
    type="object",
    description="Initial data object to send to kick a user from a community.",
    properties={
        "end_date": {
            "type": TYPE_STRING,
            "format": openapi.FORMAT_DATETIME,
            "required": True,
        },
        "reason": {"type": TYPE_STRING, "required": True},
    },
)


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="communities_create",
        operation_summary="Community create",
        operation_description="Creates a new `GamerCommunity`",
    ),
)
@method_decorator(
    name="apply",
    decorator=swagger_auto_schema(
        operation_id="communities_apply",
        operation_summary="Community apply",
        operation_description="Apply to a given community",
        request_body=serializers.CommunityApplicationSerializer,
        responses={
            201: serializers.CommunityApplicationSerializer,
            400: "You are already a member of this community.",
            403: "You are either currently banned or suspended from the community.",
        },
    ),
)
@method_decorator(
    name="leave",
    decorator=swagger_auto_schema(
        operation_summary="Community leave",
        operation_description="Leave this community",
        request_body=no_body,
        responses={
            204: "Indicates that you have been removed from the community.",
            400: "You are not a member of the community or you are the community owner and cannot leave without transferring ownership.",
        },
    ),
)
@method_decorator(
    name="transfer",
    decorator=swagger_auto_schema(
        operation_summary="Community transfer ownership",
        operation_description="Transfer ownership of the community to another admin.",
        request_body=Schema(
            title="User",
            description="Username of the admin to transfer ownership",
            type="object",
            properties={"username": {"type": "string", "format": openapi.FORMAT_SLUG}},
            required=["username"],
        ),
        responses={
            "200": serializers.GamerCommunitySerializer,
            400: "Either the username doesn't exist or they aren't an admin for the community yet.",
            403: "You are not the owner of the community.",
        },
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List communities",
        operation_description="View a list of communities.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Delete community",
        operation_description="Delete a community object.",
        responses={204: "Deleted.", 403: "You are not the owner of this community."},
        request_body=no_body,
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_summary="Community details"),
)
@method_decorator(
    name="join",
    decorator=swagger_auto_schema(
        operation_summary="Join community",
        operation_description="Join a public community.",
        request_body=no_body,
        responses={
            201: serializers.CommunityMembershipSerializer,
            400: "You are already a member of this community.",
            403: "This is either a private community or you are on an active ban or suspension from the community.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Update community details",
        operation_description="Update the community details.",
        responses={
            200: serializers.GamerCommunitySerializer,
            400: "Your data was invalid.",
            403: "You are not a community admin.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Update community details",
        operation_description="Update the community details.",
        responses={
            200: serializers.GamerCommunitySerializer,
            400: "Your data was invalid.",
            403: "You are not a community admin.",
        },
    ),
)
@parser_classes([FormParser, MultiPartParser, FileUploadParser])
class GamerCommunityViewSet(
    AutoPermissionViewSetMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    A view of a `GamerCommunity` instance.
    """

    permission_classes = (permissions.IsAuthenticated,)
    queryset = models.GamerCommunity.objects.all()
    serializer_class = serializers.GamerCommunitySerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    permission_type_map = {
        **AutoPermissionViewSetMixin.permission_type_map,
        "apply": "apply",
        "join": "join",
        "leave": "leave",
        "transfer": "delete",
    }

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

    @action(methods=["post"], detail=True, parser_classes=[JSONParser])
    def apply(self, request, **kwargs):
        """
        Apply to this community.
        """
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

    def update(self, request, **kwargs):
        logger.debug(
            "Received request to update community via api by user {}".format(
                request.user
            )
        )
        return super().update(request, **kwargs)

    def partial_update(self, request, **kwargs):
        logger.debug(
            "Received request to update community via api by user {}".format(
                request.user
            )
        )
        return super().partial_update(request, **kwargs)

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
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

    @action(methods=["post"], detail=True, parser_classes=[FormParser, JSONParser])
    def transfer(self, request, *args, **kwargs):
        """
        Transfer ownership of the community to another community admin specified by username.
        """
        community = self.get_object()
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Community: List banned users",
        operation_description="Lists all banned users for the given community. (admins only)",
        manual_parameters=[parent_lookup_community],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Community: Banned user details",
        operation_description="Details of the banned user for this community (admin only)",
        responses={
            200: serializers.BannedUserSerializer,
            403: "You are not an admin for this community",
        },
        manual_parameters=[parent_lookup_community],
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Community: Remove ban",
        operation_description="Remove the community ban indicated.",
        responses={204: "The ban was removed.", 403: "You are not a community admin."},
        manual_parameters=[
            Parameter(
                name="parent_lookup_community",
                in_="path",
                type="string",
                format=openapi.FORMAT_SLUG,
            )
        ],
    ),
)
class BannedUserViewSet(
    ParentObjectAutoPermissionViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.BannedUserSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "community"
    parent_lookup_field = "community"
    parent_object_model = models.GamerCommunity
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_community"
    permission_type_map = {**ParentObjectAutoPermissionViewSetMixin.permission_type_map}
    permission_type_map["list"] = "view"
    parent_dependent_actions = [
        "list",
        "create",
        "retrieve",
        "update",
        "partial_update",
        "destroy",
    ]

    def get_queryset(self):
        return models.BannedUser.objects.filter(
            community__slug=self.kwargs["parent_lookup_community"]
        ).select_related("banner", "banned_user")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Community: List kicked users",
        operation_description="List the kicked (supended) users from a community. (admin only)",
        manual_parameters=[parent_lookup_community],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Community: Kicked user details",
        operation_description="Details of a kicked(suspended) user",
        manual_parameters=[parent_lookup_community],
        responses={
            200: serializers.KickedUserSerializer,
            403: "You are not an admin for this community.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Community: Update kicked user details",
        operation_description="Update a kicked (suspended) user details, e.g. change the suspension date end.",
        manual_parameters=[parent_lookup_community],
        responses={
            200: serializers.KickedUserSerializer,
            403: "You are not an admin for this community.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Community: Update kicked user details",
        operation_description="Update a kicked (suspended) user details, e.g. change the suspension date end.",
        manual_parameters=[parent_lookup_community],
        responses={
            200: serializers.KickedUserSerializer,
            403: "You are not an admin for this community.",
        },
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Community: Delete kicked user",
        operation_description="Remove a kick (suspension).",
        manual_parameters=[parent_lookup_community],
        responses={
            204: "Kick was removed.",
            403: "You are not an admin for this community.",
        },
    ),
)
class KickedUserViewSet(
    ParentObjectAutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Detail view for a kicked user.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.KickedUserSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "community"
    parent_dependent_actions = {
        "list",
        "create",
        "update",
        "partial_update",
        "retrieve",
        "destroy",
    }
    parent_lookup_field = "community"
    parent_object_model = models.GamerCommunity
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_community"
    permission_type_map = {**ParentObjectAutoPermissionViewSetMixin.permission_type_map}
    permission_type_map["list"] = "view"

    def get_queryset(self):
        logger.debug("Checking data...: {}".format(self.request.data))
        return models.KickedUser.objects.filter(
            community__slug=self.kwargs["parent_lookup_community"]
        ).select_related("kicker", "kicked_user")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Community: View members",
        operation_description="View the list of members for this community.",
        manual_parameters=[parent_lookup_community],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Community: View member details",
        operation_description="View the details for a community member.",
        manual_parameters=[parent_lookup_community],
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Community: Update member",
        operation_description="Update a member record, e.g. change their role.",
        manual_parameters=[parent_lookup_community],
        responses={
            200: serializers.CommunityMembershipSerializer,
            400: "This is not a valid member of the community.",
            403: "You are not a community admin or you are trying to edit your own record.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Community: Update member",
        operation_description="Update a member record, e.g. change their role.",
        manual_parameters=[parent_lookup_community],
        responses={
            200: serializers.CommunityMembershipSerializer,
            400: "This is not a valid community member",
            403: "You are not a community admin or you are trying to edit your own record.",
        },
    ),
)
@method_decorator(
    name="kick",
    decorator=swagger_auto_schema(
        operation_summary="Community: Kick member",
        operation_description="Kick (suspend) this user from the community.",
        manual_parameters=[parent_lookup_community],
        request_body=kick_reason_schema,
        responses={
            201: serializers.KickedUserSerializer,
            400: "This is not a valid member of the community.",
            403: "Either you are not a community admin or you are trying to kick your own record.",
        },
    ),
)
@method_decorator(
    name="ban",
    decorator=swagger_auto_schema(
        operation_summary="Community: Ban member",
        operation_description="Ban this member from the community permanently.",
        manual_parameters=[parent_lookup_community],
        request_body=ban_reason_schema,
        responses={
            201: serializers.BannedUserSerializer,
            400: "This is not a valid member of the community.",
            403: "You are either not a community admin, or you are trying to ban yourself.",
        },
    ),
)
class CommunityMembershipViewSet(
    ParentObjectAutoPermissionViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset for Community membership.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.CommunityMembershipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("community", "community_role")
    parent_dependent_actions = [
        "list",
        "retrieve",
        "update",
        "partial_update",
        "destroy",
        "kick",
        "ban",
    ]
    parent_lookup_field = "community"
    parent_object_model = models.GamerCommunity
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_community"
    permission_type_map = {
        **ParentObjectAutoPermissionViewSetMixin.permission_type_map,
        "kick": "kick",
        "ban": "ban",
        "list": "view",
    }

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

    def run_check_for_member_edit(self, request, obj):
        return is_membership_subject(request.user, obj)

    def update(self, request, *args, **kwargs):
        membership = self.get_object()
        if self.run_check_for_member_edit(request, membership):
            self.permission_denied(
                request, message=_("You can't edit your own membership profile.")
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        membership = self.get_object()
        if self.run_check_for_member_edit(request, membership):
            self.permission_denied(
                request, message=_("You can't edit your own membership profile.")
            )
        return super().partial_update(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def kick(self, request, **kwargs):
        membership = self.get_object()
        if self.run_check_for_member_edit(request, membership):
            self.permission_denied(
                request, message=_("You can't edit your own membership profile.")
            )
        end_date = None
        try:
            reason = self.request.data["reason"]
        except KeyError:
            return Response(status=400)
        if "end_date" in self.request.data.keys():
            end_date = self.request.data["end_date"]
        kicker = self.request.user.gamerprofile
        try:
            kick_record = serializers.KickedUserSerializer(
                membership.community.kick_user(
                    kicker, membership.gamer, reason, earliest_reapply=end_date
                )
            )
        except PermissionDenied:
            return Response({}, status=status.HTTP_403_FORBIDDEN)
        except NotInCommunity:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        return Response(kick_record.data, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True)
    def ban(self, request, **kwargs):
        membership = self.get_object()
        if self.run_check_for_member_edit(request, membership):
            self.permission_denied(
                request, message=_("You can't edit your own membership profile.")
            )
        try:
            reason = self.request.data["reason"]
        except KeyError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        banner = self.request.user.gamerprofile
        try:
            ban_record = serializers.BannedUserSerializer(
                membership.community.ban_user(banner, membership.gamer, reason)
            )
        except PermissionDenied:
            return Response({}, status=status.HTTP_403_FORBIDDEN)
        except NotInCommunity:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ban_record.data, status=status.HTTP_201_CREATED)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Profiles",
        operation_description="List the basic profile information of for gamers based on the utilized filters.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Profile details",
        operation_description="Show details for the gamer profile in question. **NOTE**: If the active user is not connected to the gamer, they will only be able to see basic information.",
        responses={
            200: serializers.GamerProfileSerializer,
            403: "You are current blocked from seeing this user.",
        },
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Update details",
        operation_description="Update the given profile. (Only the owner may do this.)",
        request_body=serializers.GamerProfileSerializer,
        responses={
            200: serializers.GamerProfileSerializer,
            403: "You are not the owner of this profile.",
        },
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Update details",
        operation_description="Update the given profile. (Only the owner may do this.)",
        request_body=serializers.GamerProfileSerializer,
        responses={
            200: serializers.GamerProfileSerializer,
            403: "You are not the owner of this profile.",
        },
    ),
)
@method_decorator(
    name="friend",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Send friend request",
        operation_description="Send a friend request to this user.",
        request_body=no_body,
        responses={
            201: serializers.FriendRequestSerializer,
            400: "You are already friends with this user.",
            403: "You are currently blocked by this user.",
        },
    ),
)
@method_decorator(
    name="unfriend",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Unfriend user",
        operation_description="Unfriend the indicated user.",
        request_body=no_body,
        responses={
            200: "You successfully unfriended this user.",
            400: "You aren't currently friends with this user.",
        },
    ),
)
@method_decorator(
    name="block",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Block this user",
        operation_description="Block this user so that they cannot see your information, contact you, or interact with you in any way.",
        request_body=no_body,
        responses={
            201: serializers.BlockedUserSerializer,
            400: "You've already blocked this user.",
        },
    ),
)
@method_decorator(
    name="mute",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Mute user",
        operation_description="Silently mute this user so that if they contact you their messages will be silently dropped.",
        request_body=no_body,
        responses={
            201: serializers.MuteduserSerializer,
            400: "You've alredy muted this user.",
        },
    ),
)
class GamerProfileViewSet(
    AutoPermissionViewSetMixin,
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
        "adult_themes",
    )
    lookup_field = "username"
    lookup_url_kwarg = "username"
    permission_type_map = {
        **AutoPermissionViewSetMixin.permission_type_map,
        "friend": "friend",
        "unfriend": "view",
        "block": "block",
        "mute": "block",
    }

    def get_queryset(self):
        qs = models.GamerProfile.objects.all()
        return qs

    def retrieve(self, request, *args, **kwargs):
        gamer = get_object_or_404(models.GamerProfile, username=self.kwargs["username"])
        if request.user.gamerprofile.blocked_by(gamer):
            return Response(
                data={
                    "errors": "You do not have the necessary rights to retrieve this user's information."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.has_perm(
            models.GamerProfile.get_perm("view_detail"), gamer
        ):
            self.serializer_detail_class = serializers.GamerProfileListSerializer
        return Response(
            data=self.serializer_detail_class(gamer, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def friend(self, request, *args, **kwargs):
        """
        Send a friend request to the user.
        """
        target_gamer = get_object_or_404(
            models.GamerProfile, username=self.kwargs["username"]
        )
        if target_gamer in request.user.gamerprofile.friends.all():
            return Response(
                data={
                    "errors": _(
                        "{} is already one of your friends.".format(target_gamer)
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        friend_req = models.GamerFriendRequest.objects.create(
            requestor=request.user.gamerprofile, recipient=target_gamer
        )
        fr_serial = serializers.FriendRequestSerializer(friend_req)
        return Response(fr_serial.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def unfriend(self, request, *args, **kwargs):
        """
        Unfriend the user.
        """
        target_gamer = get_object_or_404(
            models.GamerProfile, username=self.kwargs["username"]
        )
        if target_gamer not in request.user.gamerprofile.friends.all():
            return Response(
                data={
                    "errors": _("{} is not one of your friends.".format(target_gamer))
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.gamerprofile.friends.remove(target_gamer)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def block(self, request, *args, **kwargs):
        """
        Blocks another user.
        """
        blockee = self.get_object()
        if blockee.user == request.user:
            return Response(
                data={"errors": "You cannot block yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if blockee.blocked_by(request.user.gamerprofile):
            return Response(
                data={"errors": "You have already blocked this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        block_record = blockee.block(request.user.gamerprofile)
        return Response(
            data=serializers.BlockedUserSerializer(block_record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def mute(self, request, *args, **kwargs):
        """
        Mutes a user. As opposed to blocking a user, this means that their messages to the muter will not be delivered, but the muted user won't know this is happening.
        """
        mutee = self.get_object()
        if mutee.user == request.user:
            return Response(
                data={"errors": "You cannot mute yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            models.MutedUser.objects.filter(
                muter=request.user.gamerprofile, mutee=mutee
            ).count()
            > 0
        ):
            return Response(
                data={"errors": "You have already muted this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        mute_record = models.MutedUser.objects.create(
            muter=request.user.gamerprofile, mutee=mutee
        )
        return Response(
            data=serializers.MuteduserSerializer(mute_record).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Profile: List notes",
        operation_description="List your notes on this user.",
        manual_parameters=[parent_lookup_profile],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Note details",
        operation_description="Show details for your note on this user.",
        manual_parameters=[parent_lookup_profile],
    ),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Add note",
        operation_description="Add a personal note about this user (only visible to you).",
        manual_parameters=[parent_lookup_profile],
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Update note details",
        operation_description="Updaet the details for your note about this user.",
        manual_parameters=[parent_lookup_profile],
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Update note details",
        operation_description="Update the details for your note about this user.",
        manual_parameters=[parent_lookup_profile],
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Profile: Delete note",
        operation_description="Delete your note about this user.",
        manual_parameters=[parent_lookup_profile],
    ),
)
class GamerNoteViewSet(
    ParentObjectAutoPermissionViewSetMixin, NestedViewSetMixin, viewsets.ModelViewSet
):
    """
    Generic view set for gamer notes.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.GamerNoteSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = "gamer"
    parent_dependent_actions = ["add", "list"]
    parent_lookup_field = "gamer"
    parent_object_model = models.GamerProfile
    parent_object_lookup_field = "username"
    parent_object_url_kwarg = "parent_lookup_gamer"
    permission_type_map = {**ParentObjectAutoPermissionViewSetMixin.permission_type_map}

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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Blocked users",
        operation_description="Fetches the list of your currently blocked users.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Blocked User: Details",
        operation_description="Details on a block record you created for a given user.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Blocked User: Unblock",
        operation_description="Unblock a given user by deleting the block record.",
        responses={204: "The user was unblocked."},
    ),
)
class BlockedUserViewSet(
    AutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    View for other users that the individual has blocked.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.BlockedUserSerializer
    permission_type_map = {**AutoPermissionViewSetMixin.permission_type_map}

    def get_queryset(self):
        return models.BlockedUser.objects.filter(
            blocker=self.request.user.gamerprofile
        ).select_related("blocker", "blockee")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Muted users",
        operation_description="Fetches the list of your currently muted users.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Muted User: Details",
        operation_description="Details on a mute record you created for a given user.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Muted User: Unmute",
        operation_description="Unblock a given user by deleting the block record.",
        responses={204: "The user was unmuted."},
    ),
)
class MutedUserViewSet(
    AutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    View for other users that the individual has muted.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.MuteduserSerializer
    permission_type_map = AutoPermissionViewSetMixin.permission_type_map

    def get_queryset(self):
        return models.MutedUser.objects.filter(
            muter=self.request.user.gamerprofile
        ).select_related("muter", "mutee")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Your Community Applications",
        operation_description="Fetch a list of all your applications to various communities.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Your Community Application: Details",
        operation_description="Details of one of your community applications.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Your Community Application: Withdraw",
        operation_description="Withdraw your community application by deleting the record.",
        responses={204: "Application was successfully withdrawn."},
    ),
)
class CommunityApplicationViewSet(
    AutoPermissionViewSetMixin,
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
    serializer_class = serializers.CommunityApplicationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("community", "status")
    permission_type_map = AutoPermissionViewSetMixin.permission_type_map

    def get_queryset(self):
        return models.CommunityApplication.objects.filter(
            gamer=self.request.user.gamerprofile
        ).select_related("community")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Community Applicants",
        operation_description="Fetch a list of applicants for the current community. (admins only)",
        manual_parameters=[parent_lookup_community],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Community Applicant: Details",
        operation_description="Get details of the applicantion to the community.",
        manual_parameters=[parent_lookup_community],
        responses={
            200: serializers.CommunityApplicationSerializer,
            403: "You are not an admin for the community.",
        },
    ),
)
@method_decorator(
    name="approve",
    decorator=swagger_auto_schema(
        operation_summary="Community Applicant: Approve",
        operation_description="Approve this application and add the user to the community.",
        manual_parameters=[parent_lookup_community],
        request_body=no_body,
        responses={
            201: serializers.CommunityMembershipSerializer,
            403: "You are not an admin for this community.",
        },
    ),
)
@method_decorator(
    name="reject",
    decorator=swagger_auto_schema(
        operation_summary="Community Applicant: Reject",
        operation_description="Reject this application.",
        manual_parameters=[parent_lookup_community],
        request_body=no_body,
        responses={
            200: serializers.CommunityApplicationSerializer,
            403: "You are not an admin for this community.",
        },
    ),
)
class CommunityAdminApplicationViewSet(
    ParentObjectAutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    View set for reviewing approving/rejecting community applications.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.CommunityApplicationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["community"]
    parent_lookup_field = "community"
    parent_object_model = models.GamerCommunity
    parent_object_lookup_field = "slug"
    parent_object_url_kwarg = "parent_lookup_community"
    parent_dependent_actions = ["list"]
    permission_type_map = {
        **ParentObjectAutoPermissionViewSetMixin.permission_type_map,
        "approve": "approve",
        "reject": "approve",
    }
    permission_type_map["list"] = "reviewlist"

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

        return obj

    @action(methods=["post"], detail=True)
    def approve(self, request, *args, **kwargs):
        """
        Approve an application.
        """
        app = self.get_object()
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
        app.reject_application()
        return Response(status=status.HTTP_202_ACCEPTED)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Sent Friend Requests",
        operation_description="Fetch a list of your pending sent friend requests.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Sent Friend Request: Details",
        operation_description="Retrieve details of a specific pending friend request.",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_summary="Sent Friend Request: Withdraw",
        operation_description="Withdraw you friend request by deleting the record.",
        request_body=no_body,
        reponses={204: "The friend request was successfully withdrawn."},
    ),
)
class SentFriendRequestViewSet(
    AutoPermissionViewSetMixin,
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
    serializer_class = serializers.FriendRequestSerializer

    def get_queryset(self):
        return models.GamerFriendRequest.objects.filter(
            requestor=self.request.user.gamerprofile, status="new"
        ).select_related("recipient")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List Received Friend Requests",
        operation_description="Fetch a list of your pending received friend requests.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Received Friend Request: Detail",
        operation_description="Get the details of a received friend request.",
    ),
)
@method_decorator(
    name="accept",
    decorator=swagger_auto_schema(
        operation_summary="Received Friend Request: Accept",
        operation_description="Accept this pending friend request and add the sender to your friends list.",
        request_body=None,
        responses={200: "Friend request accepted."},
    ),
)
@method_decorator(
    name="ignore",
    decorator=swagger_auto_schema(
        operation_summary="Received Friend Request: Ignore",
        operation_description="Ignore this received friend request.",
        request_body=no_body,
        responses={200: "Friend request ignored."},
    ),
)
class ReceivedFriendRequestViewset(
    AutoPermissionViewSetMixin,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    A view for received friend requests.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.FriendRequestSerializer
    permission_type_map = {
        **AutoPermissionViewSetMixin.permission_type_map,
        "accept": "approve",
        "ignore": "approve",
    }

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
        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True)
    def ignore(self, request, *args, **kwargs):
        """
        Ignore a friend request.
        """
        req = self.get_object()
        req.deny()
        return Response({"errors": "Ignored"}, status=status.HTTP_200_OK)
