import pytest
from test_plus import APITestCase
from ..models import (
    AlreadyInCommunity,
    NotInCommunity,
    CurrentlySuspended,
    CommunityMembership,
)
from .factories import GamerProfileFactory, GamerProfileWithCommunityFactory
from django.urls import reverse


class AbstractAPITestCase(APITestCase):
    def setUp(self):
        self.extra = {"format": "json"}
        self.gamer1 = GamerProfileWithCommunityFactory()
        self.community = CommunityMembership.objects.filter(gamer=self.gamer1)[
            0
        ].community
        self.community.set_role(self.gamer1, "admin")
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileWithCommunityFactory()


class TestCommunityViewSet(AbstractAPITestCase):
    """
    Test community viewsets.
    """

    def test_list_communities(self):
        print(reverse('api-community-list', kwargs={'format': 'json'}))
        self.get("api-community-list", extra=self.extra)
        self.response_403()
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView("api-community-list", extra=self.extra)

    def test_retrieve_community(self):
        self.get("api-community-detail", pk=self.community.pk, extra=self.extra)
        self.response_403()
        with self.login(username=self.gamer1.user.username):
            self.assertGoodView(
                "api-community-detail", pk=self.community.pk, extra=self.extra
            )
