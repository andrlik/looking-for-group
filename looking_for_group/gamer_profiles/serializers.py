from rest_framework import serializers

from ..games.models import GamePosting, Player
from ..games.serializers import GameDataSerializer
from ..users.models import User
from . import models


class GamerCommunitySerializer(serializers.ModelSerializer):
    """
    Serializer for :class:`gamer_profiles.models.GamerCommunity`.
    """

    class Meta:
        model = models.GamerCommunity
        fields = (
            "id",
            "name",
            "description",
            "url",
            "linked_with_discord",
            "private",
            "member_count",
            "created",
            "modified",
        )
        read_only_fields = (
            "id",
            "private",
            "linked_with_discord",
            "member_count",
            "created",
            "modified",
        )


class CommunityListingField(serializers.RelatedField):
    """
    Text-friendly representation for community.
    """

    queryset = models.GamerCommunity.objects.all()

    def to_representation(self, value):
        return value.name


class UserListingField(serializers.RelatedField):
    """
    Text-friendly representation for community.
    """

    queryset = User.objects.all()

    def to_representation(self, value):
        return value.display_name


class GamerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for :class:`gamer_profiles.models.GamerProfile`.
    """

    user = UserListingField()
    timezone = serializers.SerializerMethodField()
    communities = CommunityListingField(many=True)
    player_game_list = serializers.SerializerMethodField()
    gmed_games = GameDataSerializer(many=True, read_only=True)
    preferred_games = serializers.StringRelatedField(many=True, read_only=True)
    preferred_systems = serializers.StringRelatedField(many=True, read_only=True)

    def get_player_game_list(self, obj):
        games_played = GamePosting.objects.filter(
            id__in=[p.game.id for p in Player.objects.filter(gamer=obj)]
        )
        return [
            {"title": g.title, "gm": str(g.gm), "sessions": g.sessions}
            for g in games_played
        ]

    def get_timezone(self, obj):
        return obj.user.timezone

    class Meta:
        model = models.GamerProfile
        fields = (
            "user",
            "private",
            "playstyle",
            "will_gm",
            "player_status",
            "adult_themes",
            "one_shots",
            "adventures",
            "campaigns",
            "online_games",
            "local_games",
            "preferred_games",
            "preferred_systems",
            "communities",
            "reputation_score",
            "player_game_list",
            "gmed_games",
            "timezone",
        )
        read_only_fields = ("id", "user", "communities")


class CommunityMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for membership object.
    """

    community = CommunityListingField()
    gamer = GamerProfileSerializer()

    class Meta:
        model = models.CommunityMembership
        fields = (
            "id",
            "community",
            "gamer",
            "community_role",
            "median_community_rating",
            "comm_reputation_score",
            "created",
            "modified",
        )
        read_only_fields = (
            "id",
            "community",
            "gamer",
            "median_community_rating",
            "comm_reputation_score",
            "created",
            "modified",
        )


class CommunityApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for :class:`gamer_profiles.models.CommunityApplication`
    """

    community = CommunityListingField()
    gamer = GamerProfileSerializer()

    class Meta:
        model = models.CommunityApplication
        fields = (
            "id",
            "community",
            "gamer",
            "message",
            "status",
            "created",
            "modified",
        )
        read_only_fields = ("id", "community", "gamer", "created", "modified")


class GamerNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for :class:`gamer_profiles.models.GamerNote`
    """

    author = GamerProfileSerializer()
    gamer = GamerProfileSerializer()

    class Meta:
        model = models.GamerNote
        fields = ("id", "author", "gamer", "title", "body", "created", "modified")
        read_only_fields = ("id", "author", "gamer", "created", "modified")


class BlockedUserSerializer(serializers.ModelSerializer):
    """
    A serializer for :class:`gamer_profiles.models.BlockedUser`
    """

    blocker = GamerProfileSerializer()
    blockee = GamerProfileSerializer()

    class Meta:
        model = models.BlockedUser
        fields = ("id", "blocker", "blockee")
        read_only_fields = fields


class MuteduserSerializer(serializers.ModelSerializer):
    """
    A serializer for :class:`gamer_profiles.models.MutedUser`
    """

    muter = GamerProfileSerializer()
    mutee = GamerProfileSerializer()

    class Meta:
        model = models.MutedUser
        fields = ("id", "muter", "mutee")
        read_only_fields = fields


class KickedUserSerializer(serializers.ModelSerializer):
    """
    A serializer for :class:`gamer_profiles.models.KickedUser`
    """

    community = CommunityListingField()
    kicker = GamerProfileSerializer()
    kicked_user = GamerProfileSerializer()

    class Meta:
        model = models.KickedUser
        fields = ("id", "community", "kicker", "kicked_user", "end_date", "reason")
        read_only_fields = ("id", "community", "kicked_user")


class BannedUserSerializer(serializers.ModelSerializer):
    """
    A serializer for :class:`gamer_profiles.models.BannedUser`
    """

    community = CommunityListingField()
    banner = GamerProfileSerializer()
    banned_user = GamerProfileSerializer()

    class Meta:
        model = models.BannedUser
        fields = ("id", "community", "banner", "banned_user", "reason")
        read_only_fields = fields


class FriendRequestSerializer(serializers.ModelSerializer):
    """
    A serializer for friend request objects.
    """

    requestor = GamerProfileSerializer()
    recipient = GamerProfileSerializer()

    class Meta:
        model = models.GamerFriendRequest
        fields = ("id", "created", "modified", "requestor", "recipient", "status")
        read_only_fields = (
            "id",
            "created",
            "modified",
            "requestor",
            "recipient",
            "status",
        )
