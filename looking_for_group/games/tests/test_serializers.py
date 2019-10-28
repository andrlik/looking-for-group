import pytest

from ...game_catalog import models as catalog_models
from ...game_catalog import serializers as catalog_serializers
from .. import models, serializers

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "model, serializer_class",
    [
        (catalog_models.GamePublisher, catalog_serializers.GamerPublisherSerializer),
        (catalog_models.PublishedGame, catalog_serializers.PublishedGamerSerializer),
        (catalog_models.GameSystem, catalog_serializers.GameSystemSerializer),
        (catalog_models.GameEdition, catalog_serializers.GameEditionSerializer),
        (catalog_models.SourceBook, catalog_serializers.SourcebookSerializer),
        (catalog_models.PublishedModule, catalog_serializers.PublishedModuleSerializer),
    ],
)
def test_find_slug_in_url(catalog_testdata, model, serializer_class):
    """
    Test our ability to find the slugs in the testdata.
    """
    for item in model.objects.all():
        assert (
            serializers.find_slug_in_url(
                serializer_class(item, context={"request": None}).data["api_url"]
            )
            == item.slug
        )
