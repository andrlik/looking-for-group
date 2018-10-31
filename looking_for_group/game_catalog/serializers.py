import logging

from rest_framework import serializers
from taggit_serializer.serializers import TaggitSerializer, TagListSerializerField

from . import models

logger = logging.getLogger("catalog")


class GamerPublisherSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField(read_only=True)

    class Meta:
        model = models.GamePublisher
        fields = ("id", "name", "logo", "url", "tags", "created", "modified")


class GameSystemSerializer(TaggitSerializer, serializers.ModelSerializer):
    original_publisher = GamerPublisherSerializer(read_only=True)
    tags = TagListSerializerField(read_only=True)
    inherited_tags = TagListSerializerField(read_only=True)

    class Meta:
        model = models.GameSystem
        fields = (
            "id",
            "name",
            "description",
            "original_publisher",
            "image",
            "isbn",
            "publication_date",
            "ogl_license",
            "system_url",
            "created",
            "modified",
            "tags",
            "inherited_tags",
        )


class PublishedGamerSerializer(TaggitSerializer, serializers.ModelSerializer):
    game_system = GameSystemSerializer(read_only=True)
    publisher = GamerPublisherSerializer(read_only=True)
    tags = TagListSerializerField()
    inherited_tags = TagListSerializerField(read_only=True)

    class Meta:
        model = models.PublishedGame
        fields = (
            "id",
            "title",
            "edition",
            "publisher",
            "game_system",
            "image",
            "description",
            "url",
            "isbn",
            "publication_date",
            "tags",
            "inherited_tags",
        )


class PublishedModuleSerializer(TaggitSerializer, serializers.ModelSerializer):
    parent_game = PublishedGamerSerializer(read_only=True)
    publisher = GamerPublisherSerializer(read_only=True)
    tags = TagListSerializerField()
    inherited_tags = TagListSerializerField(read_only=True)

    class Meta:
        model = models.PublishedModule
        fields = (
            "id",
            "title",
            "publisher",
            "isbn",
            "publication_date",
            "parent_game",
            "image",
            "url",
            "tags",
            "inherited_tags",
        )
