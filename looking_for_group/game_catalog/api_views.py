# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework_extensions.mixins import NestedViewSetMixin

from . import models, serializers


class GamePublisherViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    List and detail views for :class:`game_catalog.models.GamePublisher`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    serializer_class = serializers.GamerPublisherSerializer
    queryset = models.GamePublisher.objects.all().prefetch_related(
        "gamesystem_set", "gameedition_set", "publishedmodule_set"
    )


class GameSystemViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and details for :class:`game_catalog.models.GameSystem`.
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


class GameEditionViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for :class:`game_catalog.models.GameEdition`.
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


class SourcebookViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for sourcebooks.
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


class PublishedGameViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for :class:`game_catalog.models.PublishedGame`.
    """

    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["publication_date"]

    serializer_class = serializers.PublishedGamerSerializer

    queryset = models.PublishedGame.objects.all().prefetch_related("editions")


class PublishedModuleViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for :class:`game_catalog.models.PublishedModule`.
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


class WideGameEditionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a non-nested list of editions
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["game", "game_system"]
    serializer_class = serializers.GameEditionSerializer
    queryset = models.GameEdition.objects.all()


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
