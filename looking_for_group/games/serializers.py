from rest_framework import serializers

from . import models


class CharacterSerializer(serializers.ModelSerializer):
    """
    Serializer for character objects.
    """

    player = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = models.Character
        fields = ("id", "name", "description", "player")


class AdventureLogSerializer(serializers.ModelSerializer):
    """
    Serializer for an adventure log.
    """

    session = serializers.PrimaryKeyRelatedField(read_only=True)
    initial_author = serializers.StringRelatedField(read_only=True)
    last_edited_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = models.AdventureLog
        fields = (
            "id",
            "session",
            "created",
            "modified",
            "initial_author",
            "last_edited_by",
            "title",
            "body",
            "body_rendered",
        )
        read_only_fields = fields


class GameSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for a game session.
    """

    adventurelog = AdventureLogSerializer()
    players_expected = serializers.StringRelatedField(many=True, read_only=True)
    players_missing = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = models.GameSession
        fields = (
            "id",
            "scheduled_time",
            "status",
            "players_expected",
            "players_missing",
            "gm_notes",
            "gm_notes_rendered",
            "adventurelog",
        )
        read_only_fields = fields


class PlayerSerializer(serializers.ModelSerializer):
    """
    Serializer for player and playerstats
    """

    gamer = serializers.StringRelatedField(read_only=True)
    game = serializers.StringRelatedField(read_only=True)
    attendance_rating = serializers.SerializerMethodField()

    def get_attendance_rating(self, obj):
        return obj.get_attendance_rating_for_game()

    class Meta:
        model = models.Player
        fields = (
            "gamer",
            "game",
            "sessions_expected",
            "sessions_missed",
            "attendance_rating",
        )
        read_only_fields = fields


class GameDataSerializer(serializers.ModelSerializer):
    """
    Serializer for game data export.
    """

    gm = serializers.StringRelatedField(read_only=True)
    players = serializers.StringRelatedField(many=True)
    published_game = serializers.StringRelatedField(read_only=True)
    game_system = serializers.StringRelatedField(read_only=True)
    published_module = serializers.StringRelatedField(read_only=True)
    communities = serializers.StringRelatedField(read_only=True)
    character_set = CharacterSerializer(many=True, read_only=True)
    gamesession_set = GameSessionSerializer(many=True, read_only=True)
    player_stats = serializers.SerializerMethodField(read_only=True)

    def get_player_stats(self, obj):
        players = models.Player.objects.filter(game=obj)
        return PlayerSerializer(players, many=True).data

    class Meta:
        model = models.GamePosting
        fields = (
            "id",
            "title",
            "gm",
            "game_description",
            "game_description_rendered",
            "game_type",
            "adult_themes",
            "content_warning",
            "published_game",
            "game_system",
            "published_module",
            "start_time",
            "session_length",
            "end_date",
            "communities",
            "players",
            "sessions",
            "gamesession_set",
            "character_set",
            "player_stats",
            "created",
            "modified",
        )
        read_only_fields = (
            "gm",
            "game_description_rendered",
            "published_game",
            "game_system",
            "published_module",
            "players",
            "gamesession_set",
            "sessions",
            "character_set",
            "created",
            "modified",
        )
