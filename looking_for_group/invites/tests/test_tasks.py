from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from test_plus import TestCase

from .. import models, tasks
from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory


class CleanUpTestCase(TestCase):
    def setUp(self):
        ContentType.objects.clear_cache()
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.community = GamerCommunityFactory(owner=self.gamer1)
        for x in range(20):
            models.Invite.objects.create(
                label="test {}".format(x),
                content_object=self.community,
                creator=self.gamer1.user,
            )

    def test_task_no_expired(self):
        assert tasks.clean_old_expired_invites() == 0

    def test_task_half_expired_but_current(self):
        invites = models.Invite.objects.all()[:10]
        for invite in invites:
            invite.expires_at = timezone.now() - timedelta(days=15)
            invite.save()
        assert tasks.clean_old_expired_invites() == 0

    def test_task_half_expired_and_old(self):
        invites = models.Invite.objects.all()[:10]
        for invite in invites:
            invite.expires_at = timezone.now() - timedelta(days=60)
            invite.save()
        assert tasks.clean_old_expired_invites() == 10
        assert models.Invite.objects.count() == 10

    def test_half_expired_but_some_accepted(self):
        invites = models.Invite.objects.all()[:10]
        for invite in invites:
            invite.expires_at = timezone.now() - timedelta(days=60)
            invite.save()
        acc_invites = models.Invite.objects.filter(status="pending")[:2]
        for invite in acc_invites:
            invite.status = "accepted"
            invite.accepted_by = self.gamer2.user
            invite.save()
            invite.expires_at = timezone.now() - timedelta(days=60)
            invite.save()
        assert tasks.clean_old_expired_invites() == 10
