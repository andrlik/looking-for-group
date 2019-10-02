# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from . import models, serializers


class GamePublisherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and detail views for :class:`game_catalog.models.GamePublisher`.
    """

    serializer_class = serializers.GamerPublisherSerializer
    queryset = models.GamePublisher.objects.all().prefetch_related(
        "gamesystem_set", "gameedition_set", "publishedmodule_set"
    )


class GameSystemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and details for :class:`game_catalog.models.GameSystem`.
    """

    filter_backends = [DjangoFilterBackend]
    # filter_backends = ["publication_date"]

    serializer_class = serializers.GameSystemSerializer

    queryset = (
        models.GameSystem.objects.all()
        .select_related("original_publisher")
        .prefetch_related("game_editions")
        .order_by("name")
    )


class GameEditionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for :class:`game_catalog.models.GameEdition`.
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["game_system", "publisher", "release_date", "game"]
    serializer_class = serializers.GameEditionSerializer
    queryset = (
        models.GameEdition.objects.all()
        .select_related("publisher")
        .prefetch_related("publishedmodule_set")
        .order_by("game__title", "release_date", "name")
    )


class SourcebookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for sourcebooks.
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["edition", "corebook"]
    serializer_class = serializers.SourcebookSerializer
    queryset = models.SourceBook.objects.all().select_related("publisher", "edition")


class PublishedGameViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for :class:`game_catalog.models.PublishedGame`.
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["publication_date"]

    serializer_class = serializers.PublishedGamerSerializer

    queryset = models.PublishedGame.objects.all().prefetch_related("editions")


class PublishedModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for :class:`game_catalog.models.PublishedModule`.
    """

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
