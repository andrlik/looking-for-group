import pytest
from django.urls import reverse
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
            self.assertResponseContains("class='button'>Apply", html=False)
            self.assertResponseContains("class='button'>Join", html=False)


class MyCommunityListView(AbstractViewTest):
    '''
    Only a user's communities should be listed.
    '''

    def test_unauthenticated_view(self):
        self.assertLoginRequired('gamer_profiles:my-community-list')

    def test_logged_in_user(self):
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView('gamer_profiles:my-community-list')
            assert len(self.get_context('object_list')) == 1
        with self.login(username=self.gamer2.user.username):
            self.assertGoodView('gamer_profiles:my-community-list')
            assert len(self.get_context('object_list')) == 1
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView("gamer_profiles:my-community-list")
            assert not self.get_context('object_list')


class CommunityDetailViewTest(AbstractViewTest):
    '''
    Test the community detail view.
    '''

    def setUp(self):
        super().setUp()
        self.view_name = 'gamer_profiles:community-detail'

    def test_unauthenticated(self):
        self.assertLoginRequired(self.view_name, community=self.community1.pk)

    def test_authenticated(self):
        with self.login(username=self.gamer1.user.username):
            print(self.community1.pk)
            print(reverse(self.view_name, kwargs={'community': self.community1.pk}))
            assert models.GamerCommunity.objects.get(pk=self.community1.pk)
            self.assertGoodView(self.view_name, community=self.community1.pk)
            self.assertGoodView(self.view_name, community=self.community2.pk)
        with self.login(username=self.gamer2.user.username):
            self.assertGoodView(self.view_name, community=self.community2.pk)
            self.get(self.view_name, self.community1.pk)
            self.response_302()
        with self.login(username=self.gamer3.user.username):
            self.assertGoodView(self.view_name, community=self.community2.pk)
            self.get(self.view_name, community=self.community1.pk)
            self.response_302()


class TestCommunityJoinView(AbstractViewTest):
    '''
    Test joining a community. Public communities should be
    easily joinable, but privates should redirect to the apply page.
    People who try to join a community they already belong to, are up
    to somethign malicious (since that isn't in the UI), and should be
    denied. Ensure that bans and kicks are enforced.
    '''
    pass
