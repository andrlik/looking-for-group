import pytest
from test_plus import TestCase
from .. import models
from . import factories


class AbstractViewTest(TestCase):
    """
    Does initial setup for all the following tests,
    which will subclass it.
    """

    def setUp(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory(private=False)
        self.community1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.community2 = factories.GamerCommunityFactory(
            owner=factories.GamerProfileFactory(), private=False
        )
        self.community2.add_member(self.gamer2)
        self.gamer3.friends.add(self.gamer1)


class TestSetup(AbstractViewTest):
    """
    Testing that the factory setup above is valid.
    """

    def test_variables(self):
        print(self.gamer1.user.display_name)
        print(self.gamer2.user.display_name)
        print(self.gamer3.user.display_name)
        assert self.community1.get_role(self.gamer1) == "Admin"
        assert self.community2.get_role(self.gamer2) == "Member"
        assert self.gamer1 in self.gamer3.friends.all()


class TestCommunityList(AbstractViewTest):
    """
    Test viewing list of all communities with limited details.
    Note, this does not require any special permissions. However,
    it should be noted that unauthenticated users should not see any
    controls. Private communities should be noted accordingly.
    """

    def test_unauthenticated_view(self):
        self.assertGoodView("gamer_profiles:community-list")
        len(self.get_context("object_list")) == 2

    def test_logged_in_user(self):
        with self.login(username=self.gamer2.user.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseContains("<span class='membership'>Member</span>")
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseContains("<span class='membership'>Admin</span>")
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView("gamer_profiles:community-list")
            self.assertResponseNotContains("<span class='membership'>")
