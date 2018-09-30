import factory.django
from django.db.models.signals import post_save
from test_plus import APITestCase
from ..models import CommunityMembership
from .factories import GamerProfileFactory, GamerProfileWithCommunityFactory


class AbstractAPITestCase(APITestCase):
    def setUp(self):
        self.extra = {"format": "json"}
        with factory.django.mute_signals(post_save):
            self.gamer1 = GamerProfileWithCommunityFactory()
            self.community = CommunityMembership.objects.filter(gamer=self.gamer1)[
                0
            ].community
            self.community.set_role(self.gamer1, "admin")
            self.gamer2 = GamerProfileFactory()
            self.gamer2.friends.add(self.gamer1)
            self.gamer3 = GamerProfileWithCommunityFactory()


class TestCommunityViewSet(AbstractAPITestCase):
    """
    Test community viewsets.
    """

    def test_list_communities(self):
        url_kwargs = {"extra": self.extra}
        self.get("api-community-list", **url_kwargs)
        print(self.last_response.data)
        self.response_403()
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("api-community-list", **url_kwargs)

    def test_retrieve_community(self):
        url_kwargs = {"pk": self.community.pk, "extra": self.extra}
        self.get("api-community-detail", **url_kwargs)
        self.response_403()
        print("Logging in with {}".format(self.gamer1.user.username))
        assert self.gamer1.user.has_perm("community.view_details", self.community)
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("api-community-detail", **url_kwargs)


class TestGamerProfileViewSet(AbstractAPITestCase):
    """
    Test gamerprofile viewset.
    """

    def test_list_profiles(self):
        self.get("api-profile-list", extra=self.extra)
        self.response_403()
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("api-profile-list", extra=self.extra)

    def test_retrieve_a_gamer_profile(self):
        url_kwargs = {"pk": self.gamer1.pk, "extra": self.extra}
        self.get("api-profile-detail", **url_kwargs)
        self.response_403()
        # assert self.gamer2.user.has_perm("profile.view_detail", self.gamer1)
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("api-profile-detail", **url_kwargs)
