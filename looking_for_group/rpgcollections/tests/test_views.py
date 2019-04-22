import pytest
from factory.django import mute_signals
from django.db.models.signals import post_save
from django.core.exceptions import ObjectDoesNotExist
from looking_for_group.gamer_profiles.tests import factories
from looking_for_group.game_catalog.tests.test_views import AbstractViewTest
from looking_for_group.rpgcollections import models


class AbstractCollectionsTest(AbstractViewTest):
    """
    Abstract base test for testing collections.
    """

    def setUp(self):
        super().setUp()
        with mute_signals(post_save):
            self.gamer1 = factories.GamerProfileFactory()
            self.gamer2 = factories.GamerProfileFactory()
            self.comm1 = factories.GamerCommunityFactory(owner=self.gamer1)
            self.comm1.add_member(self.gamer1, role="admin")
            self.gamer3 = factories.GamerProfileFactory()
            self.comm1.add_member(self.gamer2)
            self.game_lib1 = models.GameLibrary.objects.create(user=self.gamer1.user)
            self.cypher_collect_1 = models.Book.objects.create(library=self.game_lib1, content_object=self.cypher, in_print=True)
            self.game_lib2 = models.GameLibrary.objects.create(user=self.gamer2.user)
            self.game_lib3 = models.GameLibrary.objects.create(user=self.gamer3.user)


class TestViewDetail(AbstractCollectionsTest):
    """
    Test viewing a collected copy's detail.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "rpgcollections:book-detail"
        self.url_kwargs = {"book": self.cypher_collect_1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_dont_allow_unconnected(self):
        with self.login(username=self.gamer3.username):
            self.get(self.view_name, **self.url_kwargs)
            self.response_403()

    def test_friend_view(self):
        with self.login(username=self.gamer2.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_owner_view(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)


class TestEditbook(AbstractCollectionsTest):
    """
    Test updating a book.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "rpgcollections:edit-book"
        self.url_kwargs = {"book": self.cypher_collect_1.slug}
        self.post_data = {"object_id": self.cypher_collect_1.content_object.pk, "in_print": 1, "in_pdf": 1}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_unauthorized_user(self):
        for user in [self.gamer2, self.gamer3]:
            with self.login(username=user.username):
                self.get(self.view_name, **self.url_kwargs)
                self.response_403()

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)

    def test_update_data(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            tmpcheck = models.Book.objects.get(pk=self.cypher_collect_1.pk)
            assert tmpcheck.in_print and tmpcheck.in_pdf


class TestDeleteBook(AbstractCollectionsTest):
    """
    Test for deleting from a collection.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "rpgcollections:remove-book"
        self.url_kwargs = {"book": self.cypher_collect_1.slug}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_unauthorized_user(self):
        for user in [self.gamer2, self.gamer3]:
            with self.login(username=user.username):
                self.get(self.view_name, **self.url_kwargs)
                self.response_403()
                self.post(self.view_name, data={}, **self.url_kwargs)
                self.response_403()
                assert models.Book.objects.get(pk=self.cypher_collect_1.pk)

    def test_authorized_user(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name, **self.url_kwargs)
            self.post(self.view_name, data={}, **self.url_kwargs)
            self.response_302()
            with pytest.raises(ObjectDoesNotExist):
                models.Book.objects.get(pk=self.cypher_collect_1.pk)


class TestAddBook(AbstractCollectionsTest):
    """
    Test creating book records.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "rpgcollections:add-book"
        self.url_kwargs = {"booktype": "system"}
        self.post_data = {"object_id": self.cypher.pk, "in_pdf": 1}

    def test_login_required(self):
        self.assertLoginRequired(self.view_name, **self.url_kwargs)

    def test_logged_in_user(self):
        with self.login(username=self.gamer2.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert self.cypher.collected_copies.filter(library=self.game_lib2).count() > 0

    def test_add_when_aready_there(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.post_data, **self.url_kwargs)
            self.response_302()
            assert self.cypher.collected_copies.filter(library=self.game_lib1).count() == 1

    def test_bad_data(self):
        with self.login(username=self.gamer3.username):
            self.post(self.view_name, data={"object_id": self.cypher.pk}, **self.url_kwargs)
            assert len(self.get_context("collect_form").errors) > 0
