from test_plus import APITestCase
from ..models import GamePublisher, GameSystem, PublishedGame, PublishedModule
from ..serializers import (
    PublishedGamerSerializer,
    GameSystemSerializer,
    GamerPublisherSerializer,
    PublishedModuleSerializer,
)
from django.urls import reverse


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
        self.ddfive = PublishedGame(
            title="Dungeons & Dragons 5E", publisher=self.wotc, game_system=self.fivesrd
        )
        self.ddfive.save()
        self.ddfive.tags.add("fantasy")
        self.numen = PublishedGame(
            title="Numenera", publisher=self.mcg, game_system=self.cypher
        )
        self.numen.save()
        self.numen.tags.add("weird", "future", "science fantasy")
        self.cos = PublishedModule(
            title="Curse of Strahd", publisher=self.wotc, parent_game=self.ddfive
        )
        self.cos.save()
        self.cos.tags.add("horror")
        self.tiamat = PublishedModule(
            title="Rise of Tiamat", publisher=self.wotc, parent_game=self.ddfive
        )
        self.tiamat.save()
        self.tiamat.tags.add("dragons")
        self.vv = PublishedModule(
            title="Into the Violet Vale", publisher=self.mcg, parent_game=self.numen
        )
        self.vv.save()
        self.strange = PublishedGame(
            title="The Strange", publisher=self.mcg, game_system=self.cypher
        )
        self.strange.save()
        self.user1 = self.make_user("u1")
        self.pub1 = GamePublisher.objects.create(name="Monte Cook Games")


class PublisherViews(GameCatalogAbstractTestCase):
    def test_list_retrieval(self):
        self.get("api-publisher-list", extra=self.extra)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publisher-list", extra=self.extra)

    def test_detail_retrieval(self):
        url_kwargs = {"pk": self.mcg.pk}
        self.get("api-publisher-detail", **url_kwargs, extra=self.extra)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publisher-detail", **url_kwargs, extra=self.extra)
            serialized_data = GamerPublisherSerializer(self.mcg)
            assert serialized_data.data == self.last_response.data


class GameSystemViews(GameCatalogAbstractTestCase):
    def test_list_view(self):
        url_kwargs = {"extra": self.extra}
        self.get("api-system-list", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-system-list", **url_kwargs)

    def test_detail_view(self):
        url_kwargs = {"pk": self.cypher.pk, "extra": self.extra}
        self.get("api-system-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-system-detail", **url_kwargs)
            serialized_object = GameSystemSerializer(self.cypher)
            assert serialized_object.data == self.last_response.data


class PublishedGameViews(GameCatalogAbstractTestCase):
    def test_list_view(self):
        url_kwargs = {"extra": self.extra}
        self.get("api-publishedgame-list", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publishedgame-list", **url_kwargs)

    def test_detail_view(self):
        url_kwargs = {"pk": self.numen.pk, "extra": self.extra}
        self.get("api-publishedgame-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            print(
                reverse(
                    "api-publishedgame-detail",
                    kwargs={"pk": self.numen.pk, "format": "json"},
                )
            )
            self.get("api-publishedgame-detail", **url_kwargs)
            serialized_object = PublishedGamerSerializer(self.numen)
            assert serialized_object.data == self.last_response.data


class PublishedModuleViews(GameCatalogAbstractTestCase):
    def test_list_view(self):
        url_kwargs = {"extra": self.extra}
        self.get("api-publishedmodule-list", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publishedmodule-list", **url_kwargs)

    def test_detail_view(self):
        url_kwargs = {"pk": self.vv.pk, "extra": self.extra}
        self.get("api-publishedmodule-detail", **url_kwargs)
        self.response_403()
        with self.login(username=self.user1.username):
            self.get("api-publishedmodule-detail", **url_kwargs)
            serialized_object = PublishedModuleSerializer(self.vv)
            assert serialized_object.data == self.last_response.data
