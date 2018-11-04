from test_plus import TestCase

from ..models import GamePublisher, GameSystem, PublishedGame, PublishedModule, GameEdition

# Create your tests here.


class TestTagInheritance(TestCase):
    """
    Tests abstract inheritance features.
    """

    def setUp(self):
        self.parent = GamePublisher.objects.create(name="Monte Cook Games")
        self.system = GameSystem.objects.create(
            name="Cypher System", original_publisher=self.parent
        )
        self.system.tags.add("weird", "monkey")
        self.game = PublishedGame.objects.create(
            title="Numenera"
        )
        self.edition = GameEdition.objects.create(name='1', game=self.game, game_system=self.system, publisher=self.parent)
        self.edition.tags.add("discovery")
        self.module = PublishedModule.objects.create(
            title="Into the Violet Vale", publisher=self.parent, parent_game_edition=self.edition
        )
        self.module.tags.add("gencon")

    def test_inherited_tags_base_calculation(self):
        assert self.system.tags.count() == 2
        assert len(self.system.inherited_tags) == self.system.tags.count()
        assert self.edition.tags.count() == 1
        assert len(self.edition.inherited_tags) == 3
        assert self.module.tags.count() == 1
        assert len(self.module.inherited_tags) == 4

    def test_add_tag_to_parent(self):
        self.system.tags.add("fantasy")
        assert len(GameEdition.objects.get(pk=self.edition.pk).inherited_tags) == 4
        assert len(PublishedModule.objects.get(pk=self.module.pk).inherited_tags) == 5

    def test_remove_tags_from_parent(self):
        assert len(GameEdition.objects.get(pk=self.edition.pk).inherited_tags) == 3
        self.system.tags.remove("monkey")
        assert len(GameEdition.objects.get(pk=self.edition.pk).inherited_tags) == 2
        assert (
            len(PublishedModule.objects.get(pk=self.module.pk).inherited_tags) == 3
        )

    def test_remove_all_tags_from_parent(self):
        self.system.tags.clear()
        assert len(GameEdition.objects.get(pk=self.edition.pk).inherited_tags) == 1
        assert (
            len(PublishedModule.objects.get(pk=self.module.pk).inherited_tags) == 2
        )

    def test_tag_names_only(self):
        tag_names = self.edition.inherited_tag_names
        assert tag_names == ['discovery', 'monkey', 'weird']
