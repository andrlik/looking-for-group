from rest_framework import permissions, viewsets
from . import serializers, models

# Note, we don't provide create, edit, or delete views for these now as we'll handle those via the admin.


class GamePublisherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and detail views for :class:`game_catalog.models.GamePublisher`.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.GamerPublisherSerializer
    queryset = models.GamePublisher.objects.all().prefetch_related(
        "gamesystem_set", "publishedgame_set", "publishedmodule_set"
    )


class GameSystemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and details for :class:`game_catalog.models.GameSystem`.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.GameSystemSerializer

    queryset = (
        models.GameSystem.objects.all()
        .select_related("original_publisher")
        .prefetch_related("publishedgame_set")
    )


class PublishedGameViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail view for :class:`game_catalog.models.PublishedGame`.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.PublishedGamerSerializer

    queryset = (
        models.PublishedGame.objects.all()
        .select_related("publisher", "game_system")
        .prefetch_related("publishedmodule_set")
    )


class PublishedModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for :class:`game_catalog.models.PublishedModule`.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.PublishedModuleSerializer

    queryset = models.PublishedModule.objects.all().select_related(
        "publisher", "parent_game", "parent_game__game_system"
    )
