from django.urls import reverse
from test_plus import APITestCase

from ..models import GameEdition, GamePublisher, GameSystem, PublishedGame, PublishedModule, SourceBook
from ..serializers import (
    GameEditionSerializer,
    GamerPublisherSerializer,
    GameSystemSerializer,
    PublishedGamerSerializer,
    PublishedModuleSerializer,
    SourcebookSerializer
)


class GameCatalogAbstractTestCase(APITestCase):
    """
    An abstract class to make setup less repetitive.
    """

    def setUp(self):
        self.extra = {"format": "json"}
        self.mcg = GamePublisher(name="Monte Cook Games")
        self.mcg.save()
        self.wotc = GamePublisher(name="Wizards of the Coast")
        self.wotc.save()
        self.cypher = GameSystem(name="Cypher System", original_publisher=self.mcg)
        self.cypher.save()
        self.fivesrd = GameSystem(name="5E SRD", original_publisher=self.wotc)
        self.fivesrd.save()
        self.cypher.tags.add("player focused", "streamlined")
        self.fivesrd.tags.add("crunchy", "traditional")
        self.dd = PublishedGame.objects.create(title="Dungeons & Dragons")
        self.ddfive = GameEdition(name="5E", game=self.dd, publisher=self.wotc)
        self.ddfive.save()
        self.ddfive.tags.add("fantasy")
        self.numensource = PublishedGame.objects.create(title="Numenera")
        self.numen = GameEdition(name="1", game=self.numensource, publisher=self.mcg)
        self.numen.save()
        self.numen.tags.add("weird", "future", "science fantasy")
        self.cos = PublishedModule(
            title="Curse of Strahd",
            publisher=self.wotc,
            parent_game_edition=self.ddfive,
        )
        self.cos.save()
        self.cos.tags.add("horror")
        self.tiamat = PublishedModule(
            title="Rise of Tiamat", publisher=self.wotc, parent_game_edition=self.ddfive
        )
        self.tiamat.save()
        self.tiamat.tags.add("dragons")
        self.vv = PublishedModule(
            title="Into the Violet Vale",
            publisher=self.mcg,
            parent_game_edition=self.numen,
        )
        self.vv.save()
        self.discovery = SourceBook.objects.create(
            edition=self.numen, title="Numenera Discovery", publisher=self.mcg
        )
        self.strangesource = PublishedGame.objects.create(title="The Strange")
        self.strange = GameEdition(
            name="1", game=self.strangesource, publisher=self.mcg
        )
        self.strange.save()
        self.user1 = self.make_user("u1")


class PublisherViews(GameCatalogAbstractTestCase):
    def test_list_retrieval(self):
        self.get("api-publisher-list", extra=self.extra)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publisher-list", extra=self.extra)

    def test_detail_retrieval(self):
        url_kwargs = {"pk": self.mcg.pk, **self.extra}
        self.get("api-publisher-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publisher-detail", **url_kwargs)
            serialized_data = GamerPublisherSerializer(self.mcg)
            assert serialized_data.data == self.last_response.data


class GameSystemViews(GameCatalogAbstractTestCase):
    def test_list_view(self):
        url_kwargs = self.extra
        self.get("api-system-list", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-system-list", **url_kwargs)

    def test_detail_view(self):
        url_kwargs = {"pk": self.cypher.pk, **self.extra}
        self.get("api-system-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-system-detail", **url_kwargs)
            serialized_object = GameSystemSerializer(self.cypher)
            assert serialized_object.data == self.last_response.data


class PublishedGameViews(GameCatalogAbstractTestCase):
    def test_list_view(self):
        url_kwargs = self.extra
        self.get("api-publishedgame-list", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publishedgame-list", **url_kwargs)

    def test_detail_view(self):
        url_kwargs = {"pk": self.numensource.pk, **self.extra}
        print(type(self.numensource))
        self.get("api-publishedgame-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            print(reverse("api-publishedgame-detail", kwargs=url_kwargs))
            self.get("api-publishedgame-detail", **url_kwargs)
            serialized_object = PublishedGamerSerializer(self.numensource)
            assert serialized_object.data == self.last_response.data


class EditionViews(GameCatalogAbstractTestCase):
    def test_list_view(self):
        url_kwargs = {"parent_lookup_game": self.numensource.pk, **self.extra}
        self.get("api-edition-list", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-edition-list", **url_kwargs)

    def test_detail_view(self):
        url_kwargs = {
            "parent_lookup_game": self.numensource.pk,
            "pk": self.numen.pk,
            **self.extra,
        }
        self.get("api-edition-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-edition-detail", **url_kwargs)
            serialized_object = GameEditionSerializer(self.numen)
            assert serialized_object.data == self.last_response.data


class SourcebookViews(GameCatalogAbstractTestCase):
    def setUp(self):
        super().setUp()
        self.url_kwargs = {
            "parent_lookup_edition__game": self.numensource.pk,
            "parent_lookup_edition": self.numen.pk,
            **self.extra,
        }

    def test_list_view(self):
        self.get("api-sourcebook-list", **self.url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-sourcebook-list", **self.url_kwargs)

    def test_detail_view(self):
        url_kwargs = self.url_kwargs.copy()
        url_kwargs["pk"] = self.discovery.pk
        self.get("api-sourcebook-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-sourcebook-detail", **url_kwargs)
            serialized_object = SourcebookSerializer(self.discovery)
            assert serialized_object.data == self.last_response.data


class PublishedModuleViews(GameCatalogAbstractTestCase):
    def setUp(self):
        super().setUp()
        self.url_kwargs = {
            "parent_lookup_parent_game_edition__game": self.numensource.pk,
            "parent_lookup_parent_game_edition": self.numen.pk,
            **self.extra,
        }

    def test_list_view(self):
        self.get("api-publishedmodule-list", **self.url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publishedmodule-list", **self.url_kwargs)

    def test_detail_view(self):
        url_kwargs = self.url_kwargs.copy()
        url_kwargs["pk"] = self.vv.pk
        self.get("api-publishedmodule-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publishedmodule-detail", **url_kwargs)
            serialized_object = PublishedModuleSerializer(self.vv)
            assert serialized_object.data == self.last_response.data
