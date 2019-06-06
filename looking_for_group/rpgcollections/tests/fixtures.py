import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from ...game_catalog.tests.fixtures import TDataCatalogObject
from ...gamer_profiles.tests import factories
from .. import models


class CollectionTData(TDataCatalogObject):
    def __init__(self):
        super().__init__()
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.comm1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.gamer3 = factories.GamerProfileFactory()
        self.comm1.add_member(self.gamer2)
        self.game_lib1 = models.GameLibrary.objects.create(user=self.gamer1.user)
        self.cypher_collect_1 = models.Book.objects.create(library=self.game_lib1, content_object=self.cypher, in_print=True)
        self.game_lib2 = models.GameLibrary.objects.create(user=self.gamer2.user)
        self.game_lib3 = models.GameLibrary.objects.create(user=self.gamer3.user)


@pytest.fixture
def collection_testdata():
    ContentType.objects.clear_cache()
    yield CollectionTData()
    ContentType.objects.clear_cache()


@pytest.fixture(params=["book-detail", "edit-book", "remove-book"])
def collection_detail_url(request, collection_testdata):
    return reverse("rpgcollections:{}".format(request.param), kwargs={"book": getattr(collection_testdata, "cypher_collect_1").slug})
