import logging

from rest_framework import serializers
from rest_framework.reverse import reverse
from taggit_serializer.serializers import TaggitSerializer, TagListSerializerField

from . import models

logger = logging.getLogger("catalog")


class APIURLMixin:

    url_field_name = "api_url"


class NestedHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    """
    Allows to specify an arbitrary number of keyword arguments for the url in addition to the primary lookup field.
    """

    def __init__(self, view_name, parent_lookup_kwargs=None, *args, **kwargs):
        self.parent_lookup_kwargs = parent_lookup_kwargs
        super().__init__(view_name, *args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {self.lookup_url_kwarg: getattr(obj, self.lookup_field)}
        if self.parent_lookup_kwargs:
            for k, v in self.parent_lookup_kwargs.items():
                property_depth = v.split("__")
                working_property = obj
                for prop in property_depth:
                    working_property = getattr(working_property, prop)
                url_kwargs[k] = working_property
        return reverse(
            self.view_name, request=request, format=format, kwargs=url_kwargs
        )

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {self.lookup_field: view_kwargs[self.lookup_url_kwarg]}
        if self.parent_lookup_kwargs:
            for k, v in self.parent_lookup_kwargs.items():
                lookup_kwargs[v] = view_kwargs[k]
        return self.get_queryset().get(**lookup_kwargs)


class NestedHyperlinkedIdentityField(NestedHyperlinkedRelatedField):
    def __init__(self, view_name=None, **kwargs):
        assert view_name is not None, "The `view_name` argument is required."
        kwargs["read_only"] = True
        kwargs["source"] = "*"
        super().__init__(view_name, **kwargs)

    def use_pk_only_optimization(self):
        # We have the complete object instance already. We don't need
        # to run the 'only get the pk for this relationship' code.
        return False


class NestedHyperlinkedModelSerializer(
    APIURLMixin, serializers.HyperlinkedModelSerializer
):
    """
    Uses our nested hyperlinked field instead of the default.
    """

    serializer_related_field = NestedHyperlinkedRelatedField
    serializer_url_field = NestedHyperlinkedIdentityField


class GamerPublisherSerializer(
    TaggitSerializer, APIURLMixin, serializers.HyperlinkedModelSerializer
):
    tags = TagListSerializerField(read_only=True)

    class Meta:
        model = models.GamePublisher
        fields = (
            "api_url",
            "slug",
            "name",
            "logo",
            "url",
            "tags",
            "created",
            "modified",
        )
        extra_kwargs = {
            "api_url": {"view_name": "api-publisher-detail", "lookup_field": "slug"}
        }


class GameSystemSerializer(
    TaggitSerializer, APIURLMixin, serializers.HyperlinkedModelSerializer
):
    tags = TagListSerializerField(read_only=True)
    inherited_tags = TagListSerializerField(read_only=True)
    original_publisher_name = serializers.SerializerMethodField()

    def get_original_publisher_name(self, obj):
        return obj.original_publisher.name

    class Meta:
        model = models.GameSystem
        fields = (
            "api_url",
            "slug",
            "name",
            "description",
            "original_publisher",
            "original_publisher_name",
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
        extra_kwargs = {
            "api_url": {"view_name": "api-system-detail", "lookup_field": "slug"},
            "original_publisher": {
                "view_name": "api-publisher-detail",
                "lookup_field": "slug",
                "read_only": True,
            },
        }


class PublishedGamerSerializer(
    TaggitSerializer, APIURLMixin, serializers.HyperlinkedModelSerializer
):
    tags = TagListSerializerField()
    inherited_tags = TagListSerializerField(read_only=True)

    class Meta:
        model = models.PublishedGame
        fields = (
            "api_url",
            "slug",
            "title",
            "image",
            "description",
            "url",
            "publication_date",
            "tags",
            "inherited_tags",
        )
        extra_kwargs = {
            "api_url": {"view_name": "api-publishedgame-detail", "lookup_field": "slug"}
        }


class GameEditionSerializer(TaggitSerializer, NestedHyperlinkedModelSerializer):
    game = serializers.HyperlinkedRelatedField(
        view_name="api-publishedgame-detail", lookup_field="slug", read_only=True
    )
    game_title = serializers.SerializerMethodField()
    publisher = serializers.HyperlinkedRelatedField(
        view_name="api-publisher-detail", lookup_field="slug", read_only=True
    )
    publisher_name = serializers.SerializerMethodField()
    game_system = serializers.HyperlinkedRelatedField(
        view_name="api-system-detail", lookup_field="slug", read_only=True
    )
    game_system_name = serializers.SerializerMethodField()
    tags = TagListSerializerField(read_only=True)
    inherited_tags = TagListSerializerField(read_only=True)

    def get_game_title(self, obj):
        return obj.game.title

    def get_publisher_name(self, obj):
        if obj.publisher:
            return obj.publisher.name
        return None

    def get_game_system_name(self, obj):
        if obj.game_system:
            return obj.game_system.name
        return None

    class Meta:
        model = models.GameEdition
        fields = (
            "api_url",
            "slug",
            "game",
            "game_title",
            "name",
            "publisher",
            "publisher_name",
            "game_system",
            "game_system_name",
            "url",
            "release_date",
            "tags",
            "inherited_tags",
        )
        extra_kwargs = {
            "api_url": {
                "view_name": "api-edition-detail",
                "lookup_field": "slug",
                "lookup_url_kwarg": "slug",
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
            }
        }


class SourcebookSerializer(NestedHyperlinkedModelSerializer):
    publisher = serializers.HyperlinkedRelatedField(
        view_name="api-publisher-detail",
        lookup_field="slug",
        lookup_url_kwarg="slug",
        read_only=True,
    )
    publisher_name = serializers.SerializerMethodField()
    edition_title = serializers.SerializerMethodField()

    def get_publisher_name(self, obj):
        return obj.publisher.name

    def get_edition_title(self, obj):
        return "{} ({})".format(obj.edition.game.title, obj.edition.name)

    class Meta:
        model = models.SourceBook
        fields = (
            "api_url",
            "slug",
            "title",
            "image",
            "corebook",
            "publisher",
            "publisher_name",
            "edition",
            "edition_title",
            "release_date",
            "isbn",
        )
        extra_kwargs = {
            "api_url": {
                "view_name": "api-sourcebook-detail",
                "lookup_field": "slug",
                "lookup_url_kwarg": "slug",
                "parent_lookup_kwargs": {
                    "parent_lookup_edition__game__slug": "edition__game__slug",
                    "parent_lookup_edition__slug": "edition__slug",
                },
            },
            "edition": {
                "view_name": "api-edition-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
                "read_only": True,
            },
        }


class PublishedModuleSerializer(TaggitSerializer, NestedHyperlinkedModelSerializer):
    publisher = serializers.HyperlinkedRelatedField(
        view_name="api-publisher-detail", lookup_field="slug", read_only=True
    )
    tags = TagListSerializerField()
    inherited_tags = TagListSerializerField(read_only=True)
    publisher_name = serializers.SerializerMethodField()
    parent_game_edition_name = serializers.SerializerMethodField()

    def get_publisher_name(self, obj):
        return obj.publisher.name

    def get_parent_game_edition_name(self, obj):
        return "{} ({})".format(
            obj.parent_game_edition.game.title, obj.parent_game_edition.name
        )

    class Meta:
        model = models.PublishedModule
        fields = (
            "api_url",
            "slug",
            "title",
            "publisher",
            "publisher_name",
            "isbn",
            "publication_date",
            "parent_game_edition",
            "parent_game_edition_title",
            "image",
            "url",
            "tags",
            "inherited_tags",
        )
        extra_kwargs = {
            "api_url": {
                "view_name": "api-publishedmodule-detail",
                "lookup_field": "slug",
                "parent_lookup_kwargs": {
                    "parent_lookup_parent_game_edition__game__slug": "parent_game_edition__game__slug",
                    "parent_lookup_parent_game_edition__slug": "parent_game_edition__slug",
                },
            },
            "parent_game_edition": {
                "view_name": "api-edition-detail",
                "read_only": True,
                "lookup_field": "slug",
                "parent_lookup_kwargs": {"parent_lookup_game__slug": "game__slug"},
            },
        }
