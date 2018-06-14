import factory
from ...users.tests import factories as userfac
from .. import models


class GamerCommunityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GamerCommunity

    name = factory.Sequence(lambda n: "Comm %03d" % n)


class GamerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GamerProfile

    user = factory.SubFactory(userfac.UserFactory)


class CommMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CommunityMembership

    gamer = factory.SubFactory(GamerProfileFactory)
    community = factory.SubFactory(GamerCommunityFactory)


class GamerProfileWithCommunityFactory(GamerProfileFactory):
    communities = factory.RelatedFactory(CommMembershipFactory, "gamer")
