from test_plus import TestCase
from ..models import GamerNote, GamerCommunity
from .factories import GamerProfileFactory


class MarkdownConvertTestCase(TestCase):
    """
    Test that the markdown receiver is working and that it doesn't
    allow raw HTML.
    """

    def setUp(self):
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()

    def test_community_create(self):
        """
        Create a community without a markdown description.
        Rendered version should be blank.
        """
        gc = GamerCommunity.objects.create(
            name="Just some folks playing games", owner=self.gamer1
        )
        assert gc.description == gc.description_rendered

    def test_community_create_with_description(self):
        gc = GamerCommunity.objects.create(
            name="Just some folks",
            description="We are a **nice** group.",
            owner=self.gamer1,
        )
        assert gc.description != gc.description_rendered
        assert gc.description_rendered == "<p>We are a <strong>nice</strong> group.</p>"

    def test_update_community_description(self):
        gc = GamerCommunity.object.create(
            name="Just some folks",
            description="We are a **nice** group.",
            owner=self.gamer1,
        )
        gc.description = "We are a **fun** group."
        gc.save()
        assert gc.description_rendered == "<p>We are a <strong>fun</strong> group.</p>"
        gc.description = ""
        gc.save()
        assert gc.description == gc.description_rendered
        assert not gc.description_rendered

    def test_add_gamer_note(self):
        gn = GamerNote.objects.create(
            author=self.gamer1, gamer=self.gamer2, title="Silly guy", body=None
        )
        assert gn.body == gn.body_rendered
        gn2 = GamerNote.objects.create(
            author=self.gamer1,
            gamer=self.gamer2,
            title="Weirdo",
            body="Ate *all* the pizza at the game.",
        )
        assert gn2.body != gn2.body_rendered
        assert gn2.body_rendered == "<p>Ate <em>all</em> the pizza at the game.</p>"

    def test_edit_gamer_note(self):
        gn = GamerNote.objects.create(
            author=self.gamer1,
            gamer=self.gamer2,
            title="Hungry",
            body="Ate *all* the ham.",
        )
        assert gn.body_rendered == "<p>Ate <em>all</em> the ham.</p>"
        gn.body = "Ate some of the ham."
        gn.save()
        assert gn.body_rendered == "<p>Ate some of the ham.</p>"
        gn.body = None
        gn.save()
        assert gn.body == gn.body_rendered and not gn.body_rendered


class ProfileGenerationTest(TestCase):
    """
    Test signal for initial gamerprofile generation.
    """

    def test_create_user(self):
        user1 = self.make_user("u1")
        assert user1.gamerprofile
