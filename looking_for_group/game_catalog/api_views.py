# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.openapi import FORMAT_SLUG, Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework_extensions.mixins import NestedViewSetMixin

from . import models, serializers

parent_lookup_game__slug = Parameter(
    name="parent_lookup_game__slug",
    in_="path",
    type="string",
    format=FORMAT_SLUG,
    description="Slug of a parent game for an edition.",
)
parent_lookup_edition__game__slug = Parameter(
    name="parent_lookup_edition__game__slug",
    in_="path",
    type="string",
    format=FORMAT_SLUG,
    description="Slug of parent master game for a given sourcebook.",
)
parent_lookup_parent_game_edition__game__slug = Parameter(
    name="parent_lookup_parent_game_edition__game__slug",
    in_="path",
    type="string",
    format=FORMAT_SLUG,
    description="Slug of parent game for the edition this module belongs to.",
)
parent_lookup_parent_game_edition__slug = Parameter(
    name="parent_lookup_parent_game_edition__slug",
    in_="path",
    type="string",
    format=FORMAT_SLUG,
    description="Slug of edition to which this module belongs.",
)
parent_lookup_edition__slug = Parameter(
    name="parent_lookup_edition__slug",
    in_="path",
    type="string",
    format=FORMAT_SLUG,
    description="Slug of edition for which this sorucebook belongs.",
)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List of Publishers",
        operation_description="Fetch list of game publishers.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Publisher: Details",
        operation_description="Fetch details of game publisher.",
    ),
)
class GamePublisherViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    List and detail views for `GamePublisher`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    serializer_class = serializers.GamerPublisherSerializer
    queryset = models.GamePublisher.objects.all().prefetch_related(
        "gamesystem_set", "gameedition_set", "publishedmodule_set"
    )


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List of Game Systems",
        operation_description="Fetch list of game systems.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Game System: Details",
        operation_description="Fetch details of a game system.",
    ),
)
class GameSystemViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and details for `GameSystem`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    # filter_backends = ["publication_date"]

    serializer_class = serializers.GameSystemSerializer

    queryset = (
        models.GameSystem.objects.all()
        .select_related("original_publisher")
        .prefetch_related("game_editions")
        .order_by("name")
    )


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Game: List of Editions",
        operation_description="Fetch list of game editions for game.",
        manual_parameters=[parent_lookup_game__slug],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Game Edition: Details",
        operation_description="Fetch details of game edition.",
        manual_parameters=[parent_lookup_game__slug],
    ),
)
class GameEditionViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for `GameEdition`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["game_system", "publisher", "release_date", "game"]
    serializer_class = serializers.GameEditionSerializer

    def get_queryset(self):
        return (
            models.GameEdition.objects.filter(
                game__slug=self.kwargs["parent_lookup_game__slug"]
            )
            .select_related("publisher")
            .prefetch_related("publishedmodule_set")
            .order_by("game__title", "release_date", "name")
        )


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Game Edition: List of Sourcebooks",
        operation_description="Fetch list of sourcebooks for a game edition.",
        manual_parameters=[
            parent_lookup_edition__game__slug,
            parent_lookup_edition__slug,
        ],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Sourcebook: Details",
        operation_description="Fetch details of a sourcebook.",
        manual_parameters=[
            parent_lookup_edition__game__slug,
            parent_lookup_edition__slug,
        ],
    ),
)
class SourcebookViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for `Sourcebook`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["edition", "corebook"]
    serializer_class = serializers.SourcebookSerializer

    def get_queryset(self):
        return models.SourceBook.objects.filter(
            edition__game__slug=self.kwargs["parent_lookup_edition__game__slug"],
            edition__slug=self.kwargs["parent_lookup_edition__slug"],
        )


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="List of Published Games",
        operation_description="Fetch list of published games.",
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Published Game: Details",
        operation_description="Fetch details of a published game.",
    ),
)
class PublishedGameViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for `PublishedGame`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["publication_date"]

    serializer_class = serializers.PublishedGamerSerializer

    queryset = models.PublishedGame.objects.all().prefetch_related("editions")


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Game Edition: List of Modules",
        operation_description="Fetch list of modules/adventures for a game edition.",
        manual_parameters=[
            parent_lookup_parent_game_edition__game__slug,
            parent_lookup_parent_game_edition__slug,
        ],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_summary="Module: Details",
        operation_description="Fetch details of a module/adventure.",
        manual_parameters=[
            parent_lookup_parent_game_edition__game__slug,
            parent_lookup_parent_game_edition__slug,
        ],
    ),
)
class PublishedModuleViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for `PublishedModule`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "parent_game_edition",
        "publisher",
        "publication_date",
        "parent_game_edition__game_system",
    ]

    serializer_class = serializers.PublishedModuleSerializer

    queryset = models.PublishedModule.objects.all().select_related(
        "publisher",
        "parent_game_edition",
        "parent_game_edition__game",
        "parent_game_edition__game_system",
    )


@method_decorator(name="list", decorator=swagger_auto_schema(auto_schema=None))
@method_decorator(name="retrieve", decorator=swagger_auto_schema(auto_schema=None))
class WideGameEditionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a non-nested list of editions
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["game", "game_system"]
    serializer_class = serializers.GameEditionSerializer
    queryset = models.GameEdition.objects.all()


@method_decorator(name="list", decorator=swagger_auto_schema(auto_schema=None))
@method_decorator(name="retrieve", decorator=swagger_auto_schema(auto_schema=None))
class WidePublishedModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a non-nested list of modules
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "parent_game_edition",
        "parent_game_edition__game",
        "parent_game_edition__game_system",
    ]
    serializer_class = serializers.PublishedModuleSerializer
    queryset = models.PublishedModule.objects.all()
