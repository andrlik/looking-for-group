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

    game_title = serializers.SerializerMethodField()
    session_date = serializers.SerializerMethodField()
    initial_author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    last_edited_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = models.AdventureLog
        fields = (
            "api_url",
            "slug",
            "session",
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
            "session",
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
                    "parent_lookup_game__slug": "session__game__slug",
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

    adventurelog_title = serializers.SerializerMethodField()
    adventurelog_body = serializers.SerializerMethodField()
    adventurelog_body_rendered = serializers.SerializerMethodField()
    game_title = serializers.SerializerMethodField()
    players_expected = PlayerSerializer(many=True, read_only=True)
    players_missing = PlayerSerializer(many=True, read_only=True)

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
                    "parent_lookup_game__slug": "session__game__slug",
                    "parent_lookup_session__slug": "session__slug",
                },
            },
        }


class GameSessionGMSerializer(NestedUpdateMixin, GameSessionSerializer):
    """
    Serializer for a game session from the GM's view.
    """

    adventurelog = AdventureLogSerializer()
    players_expected = PlayerSerializer(many=True)
    players_missing = PlayerSerializer(many=True)

    def validate(self, data):
        data = super().validate(data)
        for player in data["players_missing"]:
            if player not in data["players_expected"]:
                raise serializers.ValidationError(
                    "You can't mark a player of missing if they weren't part of the expected set of players."
                )
        game_slug = find_slug_in_url(data["game"])
        try:
            game = models.GamePosting.objects.get(slug=game_slug)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                "You specified a game that doesn't exist!"
            )
        for player in data["players_expected"]:
            if player["game"] != game.slug:
                raise serializers.ValidationError(
                    "You cannot specify a player from another game!"
                )
        return data

    class Meta:
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


class GameDataSerializer(
    catalog_serializers.APIURLMixin, serializers.HyperlinkedModelSerializer
):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.communities.queryset = GamerProfile.objects.get(
            username=self.fields["gm"]
        ).communities.all()

    def validate(self, data):
        """
        Verify communities and catalog entries
        """
        logger.debug("Begining validation of dataset {}".format(data))
        logger.debug("Starting with basic checks...")
        data = super().validate(data)
        logger.debug("Starting on custom validation...")
        module = None
        edition = None
        system = None
        if data["privacy_level"] == "private" and data["communities"]:
            logger.debug(
                "Found an issue with someone trying to post an unlisted game to communities."
            )
            raise serializers.ValidationError(
                "You cannot post an unlisted game to communities."
            )
        if data["communities"]:
            for community_slug in data["communities"]:
                if community_slug not in [
                    c.slug
                    for c in GamerProfile.objects.get(
                        username=data["gm"]
                    ).communities.all()
                ]:
                    logger.debug(
                        "User is trying to post a game to a community of which they are not a member."
                    )
                    raise serializers.ValidationError(
                        "You cannot post a game to a community of which you are not a member. You are not a member of {}".format(
                            models.GamerCommunity.objects.get(slug=community_slug).name
                        )
                    )
        logger.debug("Starting validation of catalog entries...")
        if data["published_module"]:
            # Check to see if there is a mismatch.
            module_slug = find_slug_in_url(data["published_module"])
            logger.debug("Module is specified and found slug of {}".format(module_slug))
            try:
                module = PublishedModule.objects.get(slug=module_slug)
                logger.debug("Retrieved module {}".format(module))
            except ObjectDoesNotExist:
                raise serializers.ValidationError("You specified an invalid module.")
        if data["published_game"]:
            edition_slug = find_slug_in_url(data["published_game"])
            logger.debug("Edition is specified. Found slug of {}".format(edition_slug))
            try:
                edition = GameEdition.objects.get(slug=edition_slug)
                logger.debug("Retrieved edition object of {}".format(edition))
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    "You specified an invalid game edition."
                )

        if data["game_system"]:
            system_slug = find_slug_in_url(data["game_system"])
            logger.debug("System is specified and found slug of {}".format(system_slug))
            try:
                system = GameSystem.objects.get(slug=system_slug)
                logger.debug("Retrieved system object of {}".format(system))
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    "You specified an invalid game system."
                )
        logger.debug("Comparing retrieved catalog objects.")
        if module and edition and module.parent_game_edition != edition:
            logger.debug("Module and edition are a mismatch!!")
            raise serializers.ValidationError(
                "You specified a module that belongs to a different game edition than the one you are playing."
            )
        if edition and system and edition.game_system != system:
            logger.debug("Edition and game system are a mismatch!!")
            raise serializers.ValidationError(
                "You specified a different game system than the game edition that you are using to play."
            )
        if module and (not edition or not system):
            logger.debug(
                "Module is set, but not other values. We'll try to fill them in..."
            )
            if not edition:
                data["published_game"] = reverse(
                    "api-edition-detail",
                    kwargs={
                        "parent_lookup_game__slug": module.parent_game_edition__game__slug,
                        "slug": module.parent_game_edition.slug,
                    },
                )
                logger.debug("Set edition based on module.")
            if not system:
                data["game_system"] = reverse(
                    "api-system-detail",
                    kwargs={"slug": module.parent_game_edition.game_system.slug},
                )
                logger.debug("Set system based on module")
        elif not module and edition and not system:
            data["game_system"] = reverse(
                "api-system-detail", kwargs={"slug": edition.game_system.slug}
            )
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
            "published_game_title" "game_system_name",
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
