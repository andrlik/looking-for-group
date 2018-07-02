# import pytest
# from test_plus import APITestCase
# from ..models import (
#     AlreadyInCommunity,
#     NotInCommunity,
#     CurrentlySuspended,
#     CommunityMembership,
# )
# from .factories import GamerProfileFactory, GamerProfileWithCommunityFactory


# class AbstractAPITestCase(APITestCase):
#     def setUp(self):
#         self.extra = {"format": "json"}
#         self.gamer1 = GamerProfileWithCommunityFactory()
#         self.community = CommunityMembership.objects.filter(gamer=self.gamer1)[
#             0
#         ].community
#         self.community.set_role(self.gamer1, "admin")
#         self.gamer2 = GamerProfileFactory()
#         self.gamer3 = GamerProfileWithCommunityFactory()


# class TestCommunityViewSet(AbstractAPITestCase):
#     """
#     Test community viewsets.
#     """

#     def test_list_communities(self):
#         url_kwargs = {'extra': self.extra}
#         self.get("api-community-list", **url_kwargs)
#         self.response_403()
#         with self.login(username=self.gamer1.user.username):
#             self.assertGoodView("api-community-list", **url_kwargs)

#     def test_retrieve_community(self):
#         url_kwargs = {"pk": self.community.pk, "extra": self.extra}
#         self.get("api-community-detail", **url_kwargs)
#         self.response_403()
#         with self.login(username=self.gamer1.user.username):
#             self.assertGoodView("api-community-detail", **url_kwargs)


# class TestGamerProfileViewSet(AbstractAPITestCase):
#     '''
#     Test gamerprofile viewset.
#     '''

#     def test_retrieve_a_gamer_profile(self):
#         url_kwargs = {
#             'pk': self.gamer1.pk,
#             'extra': self.extra,
#         }
#         self.get('api-profile-detail', **url_kwargs)
#         self.response_403()
#         with self.login(username=self.gamer1.user.username):
#             self.assertGoodView('api-profile-detail', **url_kwargs)
