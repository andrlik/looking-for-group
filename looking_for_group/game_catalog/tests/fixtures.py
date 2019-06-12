from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from ...gamer_profiles.tests import factories
from .. import models


@pytest.mark.usefixtures("usertologinas")
class TDataCatalogObject(object):
    def __init__(self):
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
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.editor_group, created = Group.objects.get_or_create(name="rpgeditors")
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
        self.gamer1.refresh_from_db()
        self.gamer2.refresh_from_db()
        self.editor.refresh_from_db()


@pytest.fixture
def catalog_testdata(transactional_db):
    """
    Override the existing feature and load the additional data to the DB, but return the same fixture value.
    """
    return TDataCatalogObject()


@pytest.fixture(params=["mcg", "cypher", "numensource", "numen", "numenbook", "vv"])
def catalog_detail_url_to_check(request, catalog_testdata):
    return getattr(catalog_testdata, request.param).get_absolute_url()
