from rest_framework import viewsets

from . import models, serializers

# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.


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

    serializer_class = serializers.GameSystemSerializer

    queryset = (
        models.GameSystem.objects.all()
        .select_related("original_publisher")
        .prefetch_related("game_editions")
    )


class PublishedGameViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for :class:`game_catalog.models.PublishedGame`.
    """

    serializer_class = serializers.PublishedGamerSerializer

    queryset = (
        models.PublishedGame.objects.all().prefetch_related("editions")
    )


class PublishedModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for :class:`game_catalog.models.PublishedModule`.
    """

    serializer_class = serializers.PublishedModuleSerializer

    queryset = models.PublishedModule.objects.all().select_related(
        "publisher", "parent_game_edition", "parent_game_edition__game", "parent_game_edition__game_system"
    )
