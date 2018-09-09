from test_plus import TestCase
from .. import models


class AbstractViewTest(TestCase):
    """
    An abstract class to remove repitition from test setup.
    """

    def setUp(self):
        self.mcg = models.GamePublisher(name="Monte Cook Games")
        self.mcg.save()
        self.wotc = models.GamePublisher(name="Wizards of the Coast")
        self.wotc.save()
        self.cypher = models.GameSystem(
            name="Cypher System", original_publisher=self.mcg
        )
        self.cypher.save()
        self.fivesrd = models.GameSystem(name="5E SRD", original_publisher=self.wotc)
        self.fivesrd.save()
        self.cypher.tags.add("player focused", "streamlined")
        self.fivesrd.tags.add("crunchy", "traditional")
        self.ddfive = models.PublishedGame(
            title="Dungeons & Dragons 5E", publisher=self.wotc, game_system=self.fivesrd
        )
        self.ddfive.save()
        self.ddfive.tags.add("fantasy")
        self.numen = models.PublishedGame(
            title="Numenera", publisher=self.mcg, game_system=self.cypher
        )
        self.numen.save()
        self.numen.tags.add("weird", "future", "science fantasy")
        self.cos = models.PublishedModule(
            title="Curse of Strahd", publisher=self.wotc, parent_game=self.ddfive
        )
        self.cos.save()
        self.cos.tags.add("horror")
        self.tiamat = models.PublishedModule(
            title="Rise of Tiamat", publisher=self.wotc, parent_game=self.ddfive
        )
        self.tiamat.save()
        self.tiamat.tags.add("dragons")
        self.vv = models.PublishedModule(
            title="Into the Violet Vale", publisher=self.mcg, parent_game=self.numen
        )
        self.vv.save()
        self.strange = models.PublishedGame(
            title="The Strange", publisher=self.mcg, game_system=self.cypher
        )
        self.strange.save()


class PublisherViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:pub-list")
        assert len(self.get_context("object_list")) == 2

    def test_detail_retrieval(self):
        self.assertGoodView("game_catalog:pub-detail", publisher=self.mcg.pk)
        self.assertGoodView("game_catalog:pub-detail", publisher=self.wotc.pk)


class GameSystemViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:system-list")

    def test_detail_retrieval(self):
        self.assertGoodView("game_catalog:system-detail", system=self.cypher.pk)
        self.assertGoodView("game_catalog:system-detail", system=self.fivesrd.pk)


class PublishedGameViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:game-list")

    def test_detail_retrieval(self):
        for g in [self.numen, self.strange, self.ddfive]:
            self.assertGoodView("game_catalog:game-detail", game=g.pk)


class PublishedModuleViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:module-list")

    def test_detail_retrieval(self):
        for m in [self.cos, self.tiamat, self.vv]:
            self.assertGoodView("game_catalog:module-detail", module=m.pk)
