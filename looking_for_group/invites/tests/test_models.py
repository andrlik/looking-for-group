from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from test_plus import TestCase

from .. import models
from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory


class InviteCreationTest(TestCase):
    """
    Test creating an invite.
    """

    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = GamerProfileFactory()
        self.community = GamerCommunityFactory(owner=self.gamer1)

    def tearDown(self):
        ContentType.objects.clear_cache()
        super().tearDown()

    def test_initial_creation(self):
        invite = models.Invite.objects.create(
            label="test", content_object=self.community, creator=self.gamer1.user
        )
        assert invite.expires_at and invite.expires_at > timezone.now()
        assert invite.status == "pending"

    def test_change_status_based_on_expiration(self):
        invite = models.Invite.objects.create(
            label="test", content_object=self.community, creator=self.gamer1.user
        )
        invite.expires_at = timezone.now() - timedelta(days=10)
        invite.save()
        assert invite.status == "expired"
