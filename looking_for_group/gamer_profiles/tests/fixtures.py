import pytest

from ..tests import factories


class SocialTData(object):

    def __init__(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory(private=False)
        self.community = factories.GamerCommunityFactory(owner=factories.GamerProfileFactory())
        self.community.add_member(self.gamer1)
        self.community1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.community2 = factories.GamerCommunityFactory(
            owner=factories.GamerProfileFactory(), private=False
        )
        self.community2.add_member(self.gamer2)
        self.gamer3.friends.add(self.gamer1)


@pytest.fixture
def social_testdata(transactional_db):
    return SocialTData()


@pytest.fixture
def social_community_slug(social_testdata):
    return social_testdata.community1.slug


@pytest.fixture
def social_gamer_to_check(social_testdata):
    return social_testdata.gamer1
