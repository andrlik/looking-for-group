import logging
import re

from django.core.exceptions import ObjectDoesNotExist
from drf_writable_nested.mixins import NestedUpdateMixin
from rest_framework import serializers
from rest_framework.reverse import reverse

from ..game_catalog import serializers as catalog_serializers
from ..game_catalog.models import GameEdition, GameSystem, PublishedModule
from ..gamer_profiles.models import GamerCommunity, GamerProfile
from . import models

logger = logging.getLogger("api")


def find_slug_in_url(url):
    possible_slug = None
    if url.endswith(".json"):
        possible_slug = url[0:-5].rsplit("/", 1)[-1]
    else:
        url_to_check = url
        if url.endswith("/"):
            url_to_check = url[0:-1]
        possible_slug = url_to_check.rsplit("/", 1)[-1]
    return possible_slug


class PlayerEditableField(serializers.RelatedField):
    def to_representation(self, instance):
        return {"slug": instance.slug, "gamer": instance.gamer.username}

    def to_internal_value(self, data):
        try:
            player = models.Player.objects.get(slug=data["slug"])
        except ObjectDoesNotExist:
            return None
        return player


class CharacterSerializer(catalog_serializers.NestedHyperlinkedModelSerializer):
    """
    Serializer for character objects.
    """

    player_username = serializers.SerializerMethodField()

    def get_player_username(self, obj):
        return obj.player.gamerprofile.username

    class Meta:
        model = models.Character
        fields = ("api_url", "slug", "name", "description", "player", "player_username")
        read_only_fields = ("api_url", "slug", "player", "player_username")
        extra_kwargs = {
            "api_url": {
                "view_name": "api-character-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {
                    "parent_query_lookup__player__game__slug": "player__game__slug"
                },
            },
            "player": {"view_name": "api-profile-detail", "lookup_field": "username"},
        }


class AdventureLogSerializer(catalog_serializers.NestedHyperlinkedModelSerializer):
    """
    Serializer for an adventure log.
    """

    session = catalog_serializers.NestedHyperlinkedRelatedField(
        view_name="api-session-detail",
        lookup_field="slug",
        read_only=True,
        parent_lookup_kwargs={"parent_lookup_game__slug": "game__slug"},
    )
    game_title = serializers.SerializerMethodField()
    session_date = serializers.SerializerMethodField()
    initial_author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    last_edited_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    def __init__(self, instance=None, *args, **kwargs):
        self._supplied_session = kwargs.pop("session", None)
        super().__init__(instance, *args, **kwargs)

    def create(self, validated_data):
        validated_data.pop("session", None)
        return models.AdventureLog.objects.create(
            session=self._supplied_session, **validated_data
        )

    def get_session_date(self, obj):
        return obj.session.scheduled_time

    def get_game_title(self, obj):
        return obj.session.game.title

    def validate(self, data):
        logger.debug("Starting adventure log validation...")
        if (
            "session" not in data.keys() or not data["session"]
        ) and self._supplied_session:
            logger.debug(
                "Session is missing, but we were already supplied with a _supplied_session. Setting that as url."
            )
            data["session"] = reverse(
                "api-session-detail",
                kwargs={
                    "slug": self._supplied_session.slug,
                    "parent_lookup_game__slug": self._supplied_session.game.slug,
                },
            )
        return super().validate(data)

    class Meta:
        model = models.AdventureLog
        fields = (
            "api_url",
            "slug",
            "game_title",
            "session",
            "session_date",
            "created",
            "modified",
            "initial_author",
            "last_edited_by",
            "title",
            "body",
            "body_rendered",
        )
        read_only_fields = (
            "api_url",
            "slug",
            "game_title",
            "session",
            "session_date",
            "created",
            "modified",
            "initial_author",
            "last_edited_by",
            "body_rendered",
        )
        extra_kwargs = {
            "api_url": {
                "view_name": "api-adventurelog-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {
                    "parent_lookup_session__game__slug": "session__game__slug",
                    "parent_lookup_session__slug": "session__slug",
                },
            },
            "session": {
                "view_name": "api-session-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
            },
        }


class PlayerSerializer(serializers.ModelSerializer):
    """
    Serializer for player and playerstats
    """

    gamer = serializers.SlugRelatedField(slug_field="username", read_only=True)
    game = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    attendance_rating = serializers.SerializerMethodField()

    def get_attendance_rating(self, obj):
        return obj.get_attendance_rating_for_game()

    class Meta:
        model = models.Player
        fields = (
            "slug",
            "gamer",
            "game",
            "sessions_expected",
            "sessions_missed",
            "attendance_rating",
        )
        read_only_fields = fields


class GameSessionSerializer(catalog_serializers.NestedHyperlinkedModelSerializer):
    """
    Serializer for a game session from player's perspective.
    """

    game = catalog_serializers.NestedHyperlinkedRelatedField(
        view_name="api-game-detail", lookup_field="slug", read_only=True
    )
    adventurelog = AdventureLogSerializer()
    adventurelog_title = serializers.SerializerMethodField()
    adventurelog_body = serializers.SerializerMethodField()
    adventurelog_body_rendered = serializers.SerializerMethodField()
    game_title = serializers.SerializerMethodField()
    players_expected = serializers.SerializerMethodField(read_only=True)
    players_missing = serializers.SerializerMethodField(read_only=True)

    def get_adventurelog_title(self, obj):
        if obj.adventurelog:
            return obj.adventurelog.title
        return None

    def get_adventurelog_body(self, obj):
        if obj.adventurelog:
            return obj.adventurelog.body
        return None

    def get_adventurelog_body_rendered(self, obj):
        if obj.adventurelog:
            return obj.adventurelog.body_rendered
        return None

    def get_game_title(self, obj):
        return obj.game.title

    def get_players_expected(self, obj):
        return [p.gamer.username for p in obj.players_expected]

    def get_players_missing(self, obj):
        return [p.gamer.username for p in obj.players_missing]

    class Meta:
        model = models.GameSession
        fields = (
            "api_url",
            "slug",
            "game",
            "game_title",
            "scheduled_time",
            "status",
            "players_expected",
            "players_missing",
            "adventurelog",
            "adventurelog_title",
            "adventurelog_body",
            "adventurelog_body_rendered",
        )
        read_only_fields = fields
        extra_kwargs = {
            "api_url": {
                "view_name": "api-session-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
            },
            "game": {"view_name": "api-game-detail", "lookup_field": "slug"},
            "adventurelog": {
                "view_name": "api-adventurelog-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {
                    "parent_lookup_session__game__slug": "session__game__slug",
                    "parent_lookup_session__slug": "session__slug",
                },
            },
        }


class GameSessionGMSerializer(NestedUpdateMixin, GameSessionSerializer):
    """
    Serializer for a game session from the GM's view.
    """

    players_expected = PlayerEditableField(
        many=True, queryset=models.Player.objects.all()
    )
    players_missing = PlayerEditableField(
        many=True, queryset=models.Player.objects.all()
    )

    def validate(self, data):
        data = super().validate(data)
        logger.debug(
            "Starting check to ensure that players missing doesn't contain any elements not already in players_expected..."
        )
        for player in data["players_missing"]:
            logger.debug(
                "Checking to ensure player {} in also in {}".format(
                    player, data["players_expected"]
                )
            )
            if player not in data["players_expected"]:
                raise serializers.ValidationError(
                    "You can't mark a player of missing if they weren't part of the expected set of players."
                )
        logger.debug("Grabbing game data...")
        if self.instance or data["slug"]:
            if self.instance:
                game = self.instance.game
            else:
                game = models.GameSession.objects.get(slug=data["slug"]).game
            logger.debug("Game set to {}".format(game))
        logger.debug(
            "Parsing through players_expected value of {}".format(
                data["players_expected"]
            )
        )
        for player in data["players_expected"]:
            logger.debug(
                "Checking that player {} matches session game slug of {}".format(
                    player, game.slug
                )
            )
            if player.game.slug != game.slug:
                raise serializers.ValidationError(
                    "You cannot specify a player from another game!"
                )
        return data

    class Meta:
        model = models.GameSession
        fields = (
            "api_url",
            "slug",
            "game",
            "game_title",
            "scheduled_time",
            "status",
            "players_expected",
            "players_missing",
            "gm_notes",
            "gm_notes_rendered",
            "adventurelog",
            "adventurelog_title",
            "adventurelog_body",
            "adventurelog_body_rendered",
        )
        read_only_fields = (
            "api_url",
            "slug",
            "game",
            "game_title",
            "scheduled_time",
            "status",
            "gm_notes_rendered",
            "adventurelog",
            "adventurelog_title",
            "adventurelog_body",
            "adventurelog_body_rendered",
        )
        extra_kwargs = {
            "api_url": {
                "view_name": "api-session-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
            },
            "game": {"view_name": "api-game-detail", "lookup_field": "slug"},
            "adventurelog": {
                "view_name": "api-adventurelog-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {
                    "parent_lookup_session__game__slug": "session__game__slug",
                    "parent_lookup_session__slug": "session__slug",
                },
            },
        }


class GameDataSerializer(catalog_serializers.NestedHyperlinkedModelSerializer):
    """
    Serializer for game data export.
    """

    gm = serializers.SlugRelatedField(slug_field="username", read_only=True)
    players = serializers.SlugRelatedField(
        slug_field="username", read_only=True, many=True
    )
    published_game_title = serializers.SerializerMethodField()
    game_system_name = serializers.SerializerMethodField()
    published_module_title = serializers.SerializerMethodField()
    communities = serializers.SlugRelatedField(
        slug_field="slug", many=True, queryset=GamerCommunity.objects.all()
    )
    player_stats = serializers.SerializerMethodField(read_only=True)

    def get_player_stats(self, obj):
        players = models.Player.objects.filter(game=obj)
        return PlayerSerializer(players, many=True).data

    def get_published_game_title(self, obj):
        if obj.published_game:
            return "{} ({})".format(
                obj.published_game.game.title, obj.published_game.name
            )
        return None

    def get_game_system_name(self, obj):
        if obj.game_system:
            return obj.game_system.name
        return None

    def get_published_module_title(self, obj):
        if obj.published_module:
            return obj.published_module.title
        return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self._session_gm = self.instance.gm
            self.fields["communities"].queryset = self._session_gm.communities.all()
        elif self.context["request"] and self.context["request"].user.is_authenticated:
            self._session_gm = self.context["request"].user.gamerprofile
            self.fields["communities"].queryset = self._session_gm.communities.all()
        else:
            self._session_gm = None
            self.fields["communities"].queryset = None

    def create(self, validated_data):
        if (
            "gm" not in validated_data.keys() or not validated_data["gm"]
        ) and self._session_gm:
            return models.GamePosting.objects.create(
                gm=self._session_gm, **validated_data
            )
        return super().create(validated_data)

    def validate(self, data):
        """
        Verify communities and catalog entries
        """
        logger.debug("Begining validation of dataset {}".format(data))
        logger.debug("Updating community queryset...")
        logger.debug("Calling parent class validation basic checks...")
        data = super().validate(data)
        logger.debug("Starting on custom validation...")
        if not self.instance and not self._session_gm:
            raise serializers.ValidationError(
                {
                    "gm": "You cannot create a game without the GM being provided in the request context."
                }
            )
        if data["privacy_level"] == "private" and data["communities"]:
            logger.debug(
                "Found an issue with someone trying to post an unlisted game to communities."
            )
            raise serializers.ValidationError(
                {"communities": "You cannot post an unlisted game to communities."}
            )
        if data["communities"]:
            for community in data["communities"]:
                if community not in self._session_gm.communities.all():
                    logger.debug(
                        "User is trying to post a game to a community of which they are not a member."
                    )
                    raise serializers.ValidationError(
                        "You cannot post a game to a community of which you are not a member. You are not a member of {}".format(
                            community.name
                        )
                    )
        logger.debug("Comparing retrieved catalog objects.")
        if (
            data["published_module"]
            and data["published_game"]
            and data["published_module"].parent_game_edition != data["published_game"]
        ):
            logger.debug("Module and edition are a mismatch!!")
            raise serializers.ValidationError(
                "You specified a module that belongs to a different game edition than the one you are playing."
            )
        if (
            data["published_game"]
            and data["game_system"]
            and data["published_game"].game_system != data["game_system"]
        ):
            logger.debug("Edition and game system are a mismatch!!")
            raise serializers.ValidationError(
                "You specified a different game system than the game edition that you are using to play."
            )
        if data["published_module"] and (
            not data["published_game"] or not data["game_system"]
        ):
            logger.debug(
                "Module is set, but not other values. We'll try to fill them in..."
            )
            if not data["published_game"]:
                data["published_game"] = data["published_module"].parent_game_edition
                logger.debug("Set edition based on module.")
            if not data["game_system"]:
                data["game_system"] = data[
                    "published_module"
                ].parent_game_edition.game_system
                logger.debug("Set system based on module")
        elif (
            not data["published_module"]
            and data["published_game"]
            and not data["game_system"]
        ):
            data["game_system"] = data["published_game"].game_system
            logger.debug("Set system based on edition [module not specified.]")
        else:
            logger.debug(
                "All values parent values are already set correctly for catalog references."
            )

        return data

    class Meta:
        model = models.GamePosting
        fields = (
            "api_url",
            "slug",
            "title",
            "gm",
            "game_description",
            "game_description_rendered",
            "game_type",
            "game_status",
            "venue_type",
            "privacy_level",
            "adult_themes",
            "content_warning",
            "published_game",
            "published_game_title",
            "game_system",
            "game_system_name",
            "published_module",
            "published_module_title",
            "start_time",
            "session_length",
            "end_date",
            "communities",
            "players",
            "sessions",
            "player_stats",
            "created",
            "modified",
        )
        read_only_fields = (
            "api_url",
            "slug",
            "gm",
            "game_description_rendered",
            "published_game_title",
            "game_system_name",
            "published_module_title",
            "players",
            "sessions",
            "created",
            "modified",
        )
        extra_kwargs = {
            "api_url": {"view_name": "api-game-detail", "lookup_field": "slug"},
            "published_game": {
                "view_name": "api-edition-detail",
                "lookup_field": "slug",
                "queryset": GameEdition.objects.all().order_by("game__title", "name"),
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
            },
            "game_system": {
                "view_name": "api-system-detail",
                "lookup_field": "slug",
                "queryset": GameSystem.objects.all().order_by("name"),
            },
            "published_module": {
                "view_name": "api-publishedmodule-detail",
                "lookup_field": "slug",
                "queryset": PublishedModule.objects.all().order_by("title"),
                "parent_lookup_kwargs": {
                    "parent_lookup_parent_game_edition__game__slug": "parent_game_edition__game__slug",
                    "parent_lookup_parent_game_edition__slug": "parent_game_edition__slug",
                },
            },
        }
