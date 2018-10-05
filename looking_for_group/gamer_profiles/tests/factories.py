import factory
import factory.django
from django.db.models.signals import post_save

from .. import models
from ...users.tests import factories as userfac


@factory.django.mute_signals(post_save)
class GamerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GamerProfile

    user = factory.SubFactory(userfac.UserFactory)


# @factory.django.mute_signals(post_save)
class GamerCommunityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GamerCommunity

    name = factory.Sequence(lambda n: "Comm %03d" % n)
    owner = factory.SubFactory(GamerProfileFactory)


@factory.django.mute_signals(post_save)
class CommMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CommunityMembership

    gamer = factory.SubFactory(GamerProfileFactory)
    community = factory.SubFactory(GamerCommunityFactory)


# @factory.django.mute_signals(post_save)
class GamerProfileWithCommunityFactory(GamerProfileFactory):
    communities = factory.RelatedFactory(CommMembershipFactory, "gamer")
