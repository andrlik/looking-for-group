from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from test_plus import TestCase

from ...gamer_profiles.tests import factories
from .. import models


class BaseAbstractViewTest(object):
    """
    An abstract class to remove repitition from test setup.
    """

    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
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
        self.dd = models.PublishedGame.objects.create(title="Dungeons & Dragons")
        self.dd.tags.add("fantasy")
        self.ddfive = models.GameEdition(
            name="5E", game=self.dd, publisher=self.wotc, game_system=self.fivesrd
        )
        self.ddfive.save()
        self.numensource = models.PublishedGame(title="Numenera")
        self.numensource.save()
        self.numen = models.GameEdition.objects.create(
            name="1", game=self.numensource, publisher=self.mcg, game_system=self.cypher
        )
        self.numen.tags.add("weird", "future", "science fantasy")
        self.numenbook = models.SourceBook.objects.create(
            edition=self.numen, publisher=self.mcg, title="Numenera", corebook=True
        )
        self.cos = models.PublishedModule(
            title="Curse of Strahd",
            publisher=self.wotc,
            parent_game_edition=self.ddfive,
        )
        self.cos.save()
        self.cos.tags.add("horror")
        self.tiamat = models.PublishedModule(
            title="Rise of Tiamat", publisher=self.wotc, parent_game_edition=self.ddfive
        )
        self.tiamat.save()
        self.tiamat.tags.add("dragons")
        self.vv = models.PublishedModule(
            title="Into the Violet Vale",
            publisher=self.mcg,
            parent_game_edition=self.numen,
        )
        self.vv.save()
        self.strange_source = models.PublishedGame.objects.create(title="The Strange")
        self.strange = models.GameEdition(
            name="1",
            publisher=self.mcg,
            game=self.strange_source,
            game_system=self.cypher,
        )
        self.strange.save()

        def tearDown(self):
            ContentType.objects.clear_cache()
            super().tearDown()


class AbstractViewTest(BaseAbstractViewTest, TestCase):
    pass


class AbstractEditingViewTest(AbstractViewTest):
    """
    Handles some of the basic checks needed repeatedly for the views.
    """

    def setUp(self):
        super().setUp()
        self.editor_group, created = Group.objects.get_or_create(name="rpgeditors")
        self.superuser = self.make_user(username="superuser")
        self.superuser.is_superuser = True
        self.superuser.save()
        self.editor = factories.GamerProfileFactory()
        self.editor.user.groups.add(self.editor_group)
        self.random_gamer = factories.GamerProfileFactory()
        self.view_name = (
            "game_catalog:pub-create"
        )  # We will override this in descendent modules.
        self.url_kwargs = {}
        self.post_data = {}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_user(self):
        with self.login(username=self.random_gamer.username):
            self.get(self.view_name, **self.url_kwargs)

    def test_valid_page_load_superuser(self):
        with self.login(username=self.superuser.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_valid_page_load_editor(self):
        with self.login(username=self.editor.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class PublisherViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:pub-list")
        assert len(self.get_context("object_list")) == 2

    def test_detail_retrieval(self):
        with self.assertNumQueriesLessThan(100):
            self.get("game_catalog:pub-detail", publisher=self.mcg.pk)
            self.response_200()
            self.get("game_catalog:pub-detail", publisher=self.wotc.pk)
            self.response_200()


class PublisherCreateTest(AbstractEditingViewTest):
    """
    Test publisher creation.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:pub-create"
        self.post_data = {
            "name": "Andrlik publishing",
            "url": "https://www.andrlik.org",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            pub_count = models.GamePublisher.objects.count()
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.GamePublisher.objects.count() - pub_count == 1


class PublisherEditTest(AbstractEditingViewTest):
    """
    Test publisher editing
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:pub-edit"
        self.url_kwargs = {"publisher": self.mcg.pk}
        self.post_data = {
            "name": "Monte Cook Games 2000",
            "url": "https://www.montecookgames.com",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.GamePublisher.objects.get(pk=self.mcg.pk).name
                == "Monte Cook Games 2000"
            )


class PublisherDeleteTest(AbstractEditingViewTest):
    """
    Test deletion.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:pub-delete"
        self.url_kwargs = {"publisher": self.mcg.pk}

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.GamePublisher.objects.get(pk=self.mcg.pk)


class GameSystemViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:system-list")

    def test_detail_retrieval(self):
        self.assertGoodView("game_catalog:system-detail", system=self.cypher.pk)
        self.assertGoodView("game_catalog:system-detail", system=self.fivesrd.pk)


class GameSystemCreateTest(AbstractEditingViewTest):
    """
    Test creating a game system.
    """

    def setUp(self):
        super().setUp()
        self.evilhat = models.GamePublisher.objects.create(name="Evil Hat")
        self.view_name = "game_catalog:system-create"
        self.url_kwargs = {}
        self.post_data = {
            "name": "Forged in the dark",
            "original_publisher": self.evilhat.pk,
            "description": "I am here",
            "publication_date": "2016-09-01",
            "isbn": "",
            "system_url": "",
            "tags": "freeform, narrative",
        }

    def test_post_data(self):
        prev_count = models.GameSystem.objects.count()
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.GameSystem.objects.count() - prev_count == 1


class GameSystemEditTest(AbstractEditingViewTest):
    """
    Test for editing a game system.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:system-edit"
        self.url_kwargs = {"system": self.cypher.pk}
        self.post_data = {
            "name": "Cypher System Reloaded",
            "original_publisher": self.mcg.pk,
            "description": "So much fun",
            "publication_date": "2012-07-01",
            "isbn": "",
            "system_url": "",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.GameSystem.objects.get(pk=self.cypher.pk).name
                == "Cypher System Reloaded"
            )


class GameSystemDeleteTest(AbstractEditingViewTest):
    """
    Test Deletion of a game system
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:system-delete"
        self.url_kwargs = {"system": self.cypher.pk}

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.GameSystem.objects.get(pk=self.cypher.pk)


class GameEditionCreateTest(AbstractEditingViewTest):
    """Create test"""

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:edition_create"
        self.url_kwargs = {"game": self.numensource.pk}
        self.post_data = {
            "game_system": self.cypher.pk,
            "name": "Discovery and Destiny",
            "description": "A rewrite and expansion of the core rules adding community building.",
            "release_date": "2018-09-01",
            "tags": "community building, destiny",
            "publisher": self.mcg.pk,
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            prev_count = models.GameEdition.objects.count()
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.GameEdition.objects.count() - prev_count == 1
            assert models.GameEdition.objects.latest("created").game == self.numensource


class GameEditionEditTest(AbstractEditingViewTest):
    """
    Editing test
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:edition_edit"
        self.url_kwargs = {"edition": self.numen.slug}
        self.post_data = {
            "game_system": self.cypher.pk,
            "name": "OG",
            "description": "Explore the Ninth World",
            "publisher": self.mcg.pk,
            "release_date": "2012-07-01",
            "tags": "discovery",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.GameEdition.objects.get(pk=self.numen.pk).name == "OG"


class GameEditionDeleteTest(AbstractEditingViewTest):
    """
    Test deleting an edition.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:edition_delete"
        self.url_kwargs = {"edition": self.numen.slug}

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.GameEdition.objects.get(pk=self.numen.pk)


class GameEditionDEtailViewTest(AbstractViewTest):
    def test_detail_retrieval(self):
        self.assertGoodView("game_catalog:edition_detail", edition=self.numen.slug)


class SourcebookCreateTest(AbstractEditingViewTest):
    """
    Test creating a sourcebook
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:sourcebook_create"
        self.url_kwargs = {"edition": self.numen.slug}
        self.post_data = {
            "title": "Numenera",
            "publisher": self.mcg.pk,
            "corebook": 1,
            "release_date": "2012-07-01",
            "tags": "artwork",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            prev_count = models.SourceBook.objects.count()
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.SourceBook.objects.count() - prev_count == 1
            assert models.SourceBook.objects.latest("created").edition == self.numen


class SourcebookEditTest(AbstractEditingViewTest):
    """
    Test editing a sourcebook
    """

    def setUp(self):
        super().setUp()
        self.sb = models.SourceBook.objects.create(
            title="Numenera",
            edition=self.numen,
            publisher=self.mcg,
            release_date=datetime.strptime("2012-07-01", "%Y-%m-%d"),
        )
        self.view_name = "game_catalog:sourcebook_edit"
        self.url_kwargs = {"book": self.sb.slug}
        self.post_data = {
            "title": "Numenera OG",
            "publisher": self.mcg.pk,
            "corebook": 1,
            "release_date": "2012-07-01",
            "tags": "artwork",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.SourceBook.objects.get(pk=self.sb.pk).title == "Numenera OG"


class SourcebookDeleteTest(SourcebookEditTest):
    """
    Test deleteing a sourcebook.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:sourcebook_delete"
        self.post_data = {}

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.SourceBook.objects.get(pk=self.sb.pk)


class SourcebookDetailView(AbstractViewTest):
    def test_detail_retrieval(self):
        self.assertGoodView("game_catalog:sourcebook_detail", book=self.numenbook.slug)


class PublishedGameCreateTest(AbstractEditingViewTest):
    """
    Create a game.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:game-create"
        self.url_kwargs = {}
        self.post_data = {
            "title": "Invisible Sun",
            "description": "So strange and surreal",
            "publication_date": "2017-10-01",
            "tags": "surreal, modern, fantasy",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            prev_count = models.PublishedGame.objects.count()
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.PublishedGame.objects.count() - prev_count == 1


class PublishedGameEditTest(AbstractEditingViewTest):
    """
    Edit a game
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:game-edit"
        self.url_kwargs = {"game": self.dd.pk}
        self.post_data = {
            "title": "DND",
            "description": "Oh baby I like your way.",
            "publication_date": "1970-01-01",
            "tags": "crunchy, fantasy",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.PublishedGame.objects.get(pk=self.dd.pk).title == "DND"


class PublishedGameDeleteTest(AbstractEditingViewTest):
    """
    Test deleting a game.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:game-delete"
        self.url_kwargs = {"game": self.strange_source.pk}

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.PublishedGame.objects.get(pk=self.strange_source.pk)


class PublishedGameViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:game-list")

    def test_detail_retrieval(self):
        for g in [self.numensource, self.strange_source, self.dd]:
            self.assertGoodView("game_catalog:game-detail", game=g.pk)


class PublishedModuleCreateTest(AbstractEditingViewTest):
    """
    Test creating a published module
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:module-create"
        self.url_kwargs = {"edition": self.strange.slug}
        self.post_data = {
            "title": "The Dark Spiral",
            "publisher": self.mcg.pk,
            "publication_date": "2013-10-15",
            "tags": "world hopping, advanced",
            "isbn": "",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            prev_count = models.PublishedModule.objects.count()
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.PublishedModule.objects.count() - prev_count == 1
            assert (
                models.PublishedModule.objects.latest("created").parent_game_edition
                == self.strange
            )


class PublishedModuleEditTest(AbstractEditingViewTest):
    """
    Test Editing a module
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:module-edit"
        self.url_kwargs = {"module": self.cos.pk}
        self.post_data = {
            "title": "RAVENLOFT!!!!",
            "publisher": self.wotc.pk,
            "publication_date": "2016-11-01",
            "tags": "horror, nonlinear",
            "isbn": "",
        }

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.PublishedModule.objects.get(pk=self.cos.pk).title
                == "RAVENLOFT!!!!"
            )


class PublishedModuleDeleteTest(AbstractEditingViewTest):
    """
    Delete a module
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:module-delete"
        self.url_kwargs = {"module": self.vv.pk}

    def test_post_data(self):
        with self.login(username=self.editor.username):
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.PublishedModule.objects.get(pk=self.vv.pk)


class PublishedModuleViews(AbstractViewTest):
    def test_list_retrieval(self):
        self.assertGoodView("game_catalog:module-list")

    def test_detail_retrieval(self):
        for m in [self.cos, self.tiamat, self.vv]:
            self.assertGoodView("game_catalog:module-detail", module=m.pk)


class RecentAdditionViewTest(AbstractViewTest):
    """
    Basic test for the recent additions view
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:recent_additions"

    def test_list_retrieval(self):
        with self.assertNumQueriesLessThan(150):
            self.get(self.view_name)
            self.response_200()


class AbstractSuggestedCorrectionAdditionTest(AbstractViewTest):
    """
    An abstract base class that allows us to prepopulate some needed values.
    """

    def setUp(self):
        super().setUp()
        self.editor_group, created = Group.objects.get_or_create(name="rpgeditors")
        self.superuser = self.make_user(username="superuser")
        self.superuser.is_superuser = True
        self.superuser.save()
        self.editor = factories.GamerProfileFactory()
        self.editor.user.groups.add(self.editor_group)
        self.random_gamer = factories.GamerProfileFactory()
        self.correction1 = models.SuggestedCorrection.objects.create(
            new_title="OG Numenera",
            new_description="Show em your **bad** cypher self.",
            new_url="https://www.google.com",
            new_release_date=timezone.now() - timedelta(days=30),
            submitter=self.gamer1.user,
            other_notes="You might want to update the cover...",
            content_object=self.numen,
        )
        self.addition1 = models.SuggestedAddition.objects.create(
            content_type=ContentType.objects.get_for_model(models.GameEdition),
            title="Numenera 4",
            description="The next generation",
            release_date=timezone.now() + timedelta(days=400),
            suggested_tags="future, wild",
            game=self.numensource,
            publisher=self.mcg,
            system=self.cypher,
            submitter=self.gamer1.user,
        )
        self.gamer2.user.groups.add(self.editor_group)
        # TODO: Add more cases here for use.


class SuggestedCorrectionListView(AbstractSuggestedCorrectionAdditionTest):
    """
    Test list view for suggested corrections.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:correction_list"

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name)


class SuggestedCorrectionCreateTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test for creating a suggested correction.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:correction_create"
        self.url_kwargs = {"objtype": "edition", "object_id": self.numen.pk}
        self.post_data = {
            "new_title": "Future monkeys are us",
            "new_url": "https://www.google.com",
            "new_description": "I ate something and now I feel bad.",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_test_mismatch_type(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, objtype="publisher", object_id=self.numen.pk)
            self.response_404()

    def test_correct_data(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.SuggestedCorrection.objects.latest('created').new_title
                == "Future monkeys are us"
            )


class SuggestedCorrectionUpdateTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test for updating a suggested correction
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:correction_update"
        self.url_kwargs = {"correction": self.correction1.slug}
        self.post_data = {
            "new_title": "Future monkeys are us",
            "new_url": "https://www.google.com",
            "new_description": "I ate something and now I feel bad.",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.SuggestedCorrection.objects.get(id=self.correction1.pk).new_title
                == "Future monkeys are us"
            )


class SuggestedCorrectionDetailTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test detail view.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:correction_detail"
        self.url_kwargs = {"correction": self.correction1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class SuggestedCorrectionDeleteTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test deleting a correction.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:correction_delete"
        self.url_kwargs = {"correction": self.correction1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data={}, **self.url_kwargs)
            with pytest.raises(ObjectDoesNotExist):
                models.SuggestedCorrection.objects.get(id=self.correction1.pk)


class SuggestedCorrectionApproveDenyTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test approval and deny modes for corrections.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:correction_review"
        self.url_kwargs = {"correction": self.correction1.slug}
        self.approve_data = {"approve": 1}
        self.deny_data = {"reject": 1}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_post_required(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_405()

    def test_unauthrorized_user(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.approve_data, **self.url_kwargs)
            self.response_403()
            assert (
                models.SuggestedCorrection.objects.get(id=self.correction1.pk).status
                == "new"
            )

    def test_authorized_deny(self):
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.deny_data, **self.url_kwargs)
            assert (
                models.SuggestedCorrection.objects.get(id=self.correction1.pk).status
                == "rejected"
            )

    def test_authorized_approval(self):
        tag_count = self.correction1.content_object.tags.count()
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.approve_data, **self.url_kwargs)
            obj = models.SuggestedCorrection.objects.get(id=self.correction1.pk)
            source_obj = obj.content_object
            assert source_obj.tags.count() - tag_count == 0
            assert obj.status == "approved"
            assert source_obj.name == obj.new_title
            assert source_obj.description == obj.new_description

    def test_omit_change(self):
        self.correction1.new_title = None
        self.correction1.save()
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.approve_data, **self.url_kwargs)
            obj = models.SuggestedCorrection.objects.get(id=self.correction1.pk)
            source_obj = obj.content_object
            assert obj.status == "approved"
            assert source_obj.name and obj.new_title != source_obj.name
            assert source_obj.description == obj.new_description


class SuggestedAdditionListView(AbstractSuggestedCorrectionAdditionTest):
    """
    Test list view for suggested addition.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:addition_list"

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name)


class SuggestedAdditionCreateTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test creating a new addition.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:addition_create"
        self.url_kwargs = {"obj_type": "publisher"}
        self.post_data = {
            "title": "Future monkeys are us",
            "publisher": self.mcg.pk,
            "system": self.cypher.pk,
            "description": "I ate something and now I feel bad.",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_invalid_obj_type(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, obj_type="monkey")
            self.response_404()

    def test_valid_obj_type(self):
        current_additions = models.SuggestedAddition.objects.count()
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert models.SuggestedAddition.objects.count() - current_additions == 1


class SuggestedAdditionUpdateTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test for updating a suggested addition.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:addition_update"
        self.url_kwargs = {"addition": self.addition1.slug}
        self.post_data = {
            "title": "Future monkeys are us",
            "publisher": self.mcg.pk,
            "system": self.cypher.pk,
            "game": self.numensource.pk,
            "description": "I ate something and now I feel bad.",
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            assert (
                models.SuggestedAddition.objects.get(id=self.addition1.pk).title
                == "Future monkeys are us"
            )


class SuggestedAdditionDetailTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test detail view for suggested addition.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:addition_detail"
        self.url_kwargs = {"addition": self.addition1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class SuggestedAdditionDeleteTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test delete view for suggested addition.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:addition_delete"
        self.url_kwargs = {"addition": self.addition1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_incorrect_user(self):
        with self.login(username=self.gamer1.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data={}, **self.url_kwargs)
            with pytest.raises(ObjectDoesNotExist):
                models.SuggestedAddition.objects.get(id=self.addition1.pk)


class SuggestedAdditionApproveDenyTest(AbstractSuggestedCorrectionAdditionTest):
    """
    Test approving and denying additions and that records are updated correctly.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "game_catalog:addition_review"
        self.url_kwargs = {"addition": self.addition1.slug}
        self.approve_data = {"approve": 1}
        self.reject_data = {"reject": 1}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_post_required(self):
        with self.login(username=self.gamer2.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_405()

    def test_unauthorized_user(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.reject_data, **self.url_kwargs)
            self.response_403()
            assert (
                models.SuggestedAddition.objects.get(id=self.addition1.pk).status
                == "new"
            )

    def test_authorized_reject(self):
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.reject_data, **self.url_kwargs)
            assert (
                models.SuggestedAddition.objects.get(id=self.addition1.pk).status
                == "rejected"
            )

    def test_authorized_approval(self):
        original_edition_count = models.GameEdition.objects.count()
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.approve_data, **self.url_kwargs)
            assert models.GameEdition.objects.count() - original_edition_count == 1
            assert (
                models.SuggestedAddition.objects.get(id=self.addition1.pk).status
                == "approved"
            )
