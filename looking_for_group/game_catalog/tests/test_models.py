from hashlib import sha1

import pytest
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from test_plus import TestCase

from ...gamer_profiles.tests import factories
from ..models import (
    GameEdition,
    GamePublisher,
    GameSystem,
    PublishedGame,
    PublishedModule,
    SourceBook,
    SuggestedAddition,
    SuggestedCorrection
)

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
        self.game = PublishedGame.objects.create(title="Numenera")
        self.edition = GameEdition.objects.create(
            name="1", game=self.game, game_system=self.system, publisher=self.parent
        )
        self.edition.tags.add("discovery")
        self.module = PublishedModule.objects.create(
            title="Into the Violet Vale",
            publisher=self.parent,
            parent_game_edition=self.edition,
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
        assert len(PublishedModule.objects.get(pk=self.module.pk).inherited_tags) == 3

    def test_remove_all_tags_from_parent(self):
        self.system.tags.clear()
        assert len(GameEdition.objects.get(pk=self.edition.pk).inherited_tags) == 1
        assert len(PublishedModule.objects.get(pk=self.module.pk).inherited_tags) == 2

    def test_tag_names_only(self):
        tag_names = self.edition.inherited_tag_names
        assert tag_names == ["discovery", "monkey", "weird"]


class TestMarkdown(TestCase):
    """
    Test markdown conversion.
    """

    def test_published_game(self):
        pg = PublishedGame.objects.create(
            title="Johnson", description="I'm **strong**!"
        )
        assert pg.description_rendered == "<p>I'm <strong>strong</strong>!</p>"


class AbstractImageMoveTest(TestCase):
    """
    Test functions for migrating images between objects.
    """

    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = factories.GamerProfileFactory()
        self.numensource = PublishedGame.objects.create(
            title="Numenera", description="I'm **strong**!"
        )
        self.mcg = GamePublisher.objects.create(name="Monte Cook Games")
        self.cypher = GameSystem.objects.create(
            name="Cypher System", original_publisher=self.mcg
        )
        self.numen = GameEdition.objects.create(
            name="1", publisher=self.mcg, game_system=self.cypher, game=self.numensource
        )
        self.numenbook = SourceBook.objects.create(
            title="Numenera", corebook=True, publisher=self.mcg, edition=self.numen
        )
        self.test_image_path = "{}/game_catalog/tests/test_image.png".format(
            settings.APPS_DIR
        )
        self.game_correction = SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            new_title="Numenera OG",
            content_object=self.numensource,
        )
        self.pub_correction = SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            new_title="Monte Cook Cribs",
            content_object=self.mcg,
        )
        self.edition_correction = SuggestedCorrection.objects.create(
            submitter=self.gamer1.user, new_title="OG", content_object=self.numen
        )
        self.sys_correction = SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            new_title="Cypher System (Original)",
            content_object=self.cypher,
        )
        self.book_correction = SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            new_title="Numenera OG Corebook",
            content_object=self.numenbook,
        )
        for x in [
            self.game_correction,
            self.pub_correction,
            self.sys_correction,
            self.book_correction,
            self.edition_correction,
        ]:
            with open(self.test_image_path, "rb") as f:
                myfile = File(f)
                x.new_image.save("test_image.png", myfile, save=True)
        self.pub_addition = SuggestedAddition.objects.create(
            title="Evil Hat Productions",
            submitter=self.gamer1.user,
            content_type=ContentType.objects.get_for_model(GamePublisher),
        )
        self.game_addition = SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            title="Blades in the Dark",
            content_type=ContentType.objects.get_for_model(PublishedGame),
        )
        self.edition_addition = SuggestedAddition.objects.create(
            title="Discovery and Destiny",
            submitter=self.gamer1.user,
            content_type=ContentType.objects.get_for_model(GameEdition),
            game=self.numensource,
            publisher=self.mcg,
            system=self.cypher,
        )
        self.system_addition = SuggestedAddition.objects.create(
            title="Cypher System Revised",
            submitter=self.gamer1.user,
            content_type=ContentType.objects.get_for_model(GameSystem),
            publisher=self.mcg,
        )
        self.book_addition = SuggestedAddition.objects.create(
            title="Love and Sex in the Ninth World",
            submitter=self.gamer1.user,
            content_type=ContentType.objects.get_for_model(SourceBook),
            publisher=self.mcg,
            edition=self.numen,
        )
        for x in [
            self.pub_addition,
            self.game_addition,
            self.edition_addition,
            self.system_addition,
            self.book_addition,
        ]:
            with open(self.test_image_path, "rb") as f:
                myfile = File(f)
                x.image.save("test_image.png", myfile, save=True)

    def tearDown(self):
        ContentType.objects.clear_cache()
        super().tearDown()


class CorrectionImageMoveTest(AbstractImageMoveTest):
    def test_migrate_image_to_publisher(self):
        print("Starting test to migrate image to publisher...")
        orig_hash = sha1(self.pub_correction.new_image.read())
        self.pub_correction.new_image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.pub_correction.transfer_image("logo")
        print("Running integrity checks...")
        self.pub_correction.refresh_from_db()
        assert not self.pub_correction.new_image.name
        print("Image is no longer in correction image...")
        self.mcg.refresh_from_db()
        assert self.mcg.logo.name
        print("Image IS in field on publisher... verifying hashs.")
        new_hash = sha1(self.mcg.logo.read())
        self.mcg.logo.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_to_wrong_attribute(self):
        with pytest.raises(KeyError):
            self.pub_correction.transfer_image()

    def test_migrate_non_file(self):
        self.pub_correction.new_image.delete()
        with pytest.raises(ValueError):
            self.pub_correction.transfer_image("logo")

    def test_migrate_image_to_game(self):
        print("Starting test to migrate image to game...")
        orig_hash = sha1(self.game_correction.new_image.read())
        self.game_correction.new_image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.game_correction.transfer_image()
        print("Running integrity checks...")
        self.game_correction.refresh_from_db()
        assert not self.game_correction.new_image.name
        print("Image is no longer in correction image...")
        self.numensource.refresh_from_db()
        assert self.numensource.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.numensource.image.read())
        self.numensource.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_image_to_system(self):
        print("Starting test to migrate image to system...")
        orig_hash = sha1(self.sys_correction.new_image.read())
        self.sys_correction.new_image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.sys_correction.transfer_image()
        print("Running integrity checks...")
        self.sys_correction.refresh_from_db()
        assert not self.sys_correction.new_image.name
        print("Image is no longer in correction image...")
        self.cypher.refresh_from_db()
        assert self.cypher.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.cypher.image.read())
        self.cypher.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_image_to_edition(self):
        print("Starting test to migrate image to game...")
        orig_hash = sha1(self.edition_correction.new_image.read())
        self.edition_correction.new_image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.edition_correction.transfer_image()
        print("Running integrity checks...")
        self.edition_correction.refresh_from_db()
        assert not self.edition_correction.new_image.name
        print("Image is no longer in correction image...")
        self.numen.refresh_from_db()
        assert self.numen.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.numen.image.read())
        self.numen.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_image_to_sourcebook(self):
        print("Starting test to migrate image to sourcebook...")
        orig_hash = sha1(self.book_correction.new_image.read())
        self.book_correction.new_image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.book_correction.transfer_image()
        print("Running integrity checks...")
        self.book_correction.refresh_from_db()
        assert not self.book_correction.new_image.name
        print("Image is no longer in correction image...")
        self.numenbook.refresh_from_db()
        assert self.numenbook.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.numenbook.image.read())
        self.numenbook.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()


class AdditionImageMoveTest(AbstractImageMoveTest):
    def test_migrate_game_addition_publisher(self):
        print("Starting test to migrate image to publisher...")
        orig_hash = sha1(self.pub_addition.image.read())
        self.pub_addition.image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.pub_addition.transfer_image(self.mcg, "logo")
        print("Running integrity checks...")
        self.pub_addition.refresh_from_db()
        assert not self.pub_addition.image.name
        print("Image is no longer in addition image...")
        self.mcg.refresh_from_db()
        assert self.mcg.logo.name
        print("Image IS in field on publisher... verifying hashs.")
        new_hash = sha1(self.mcg.logo.read())
        self.mcg.logo.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_to_wrong_attribute(self):
        with pytest.raises(KeyError):
            self.pub_addition.transfer_image(self.mcg)

    def test_migrate_non_file(self):
        self.pub_addition.image.delete()
        with pytest.raises(ValueError):
            self.pub_addition.transfer_image(self.mcg, "logo")

    def test_migrate_image_to_game(self):
        print("Starting test to migrate image to game...")
        orig_hash = sha1(self.game_addition.image.read())
        self.game_addition.image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.game_addition.transfer_image(self.numensource)
        print("Running integrity checks...")
        self.game_addition.refresh_from_db()
        assert not self.game_addition.image.name
        print("Image is no longer in addition image...")
        self.numensource.refresh_from_db()
        assert self.numensource.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.numensource.image.read())
        self.numensource.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_image_to_system(self):
        print("Starting test to migrate image to system...")
        orig_hash = sha1(self.system_addition.image.read())
        self.system_addition.image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.system_addition.transfer_image(self.cypher)
        print("Running integrity checks...")
        self.sys_correction.refresh_from_db()
        assert not self.system_addition.image.name
        print("Image is no longer in addition image...")
        self.cypher.refresh_from_db()
        assert self.cypher.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.cypher.image.read())
        self.cypher.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_image_to_edition(self):
        print("Starting test to migrate image to game...")
        orig_hash = sha1(self.edition_addition.image.read())
        self.edition_addition.image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.edition_addition.transfer_image(self.numen)
        print("Running integrity checks...")
        self.edition_addition.refresh_from_db()
        assert not self.edition_addition.image.name
        print("Image is no longer in addition image...")
        self.numen.refresh_from_db()
        assert self.numen.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.numen.image.read())
        self.numen.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()

    def test_migrate_image_to_sourcebook(self):
        print("Starting test to migrate image to sourcebook...")
        orig_hash = sha1(self.book_addition.image.read())
        self.book_addition.image.close()
        print("Orginal hash is {}".format(orig_hash.hexdigest()))
        self.book_addition.transfer_image(self.numenbook)
        print("Running integrity checks...")
        self.book_addition.refresh_from_db()
        assert not self.book_addition.image.name
        print("Image is no longer in addition image...")
        self.numenbook.refresh_from_db()
        assert self.numenbook.image.name
        print("Image IS in field on game... verifying hashs.")
        new_hash = sha1(self.numenbook.image.read())
        self.numenbook.image.close()
        assert orig_hash.hexdigest() == new_hash.hexdigest()
