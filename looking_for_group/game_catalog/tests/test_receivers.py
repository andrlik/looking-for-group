from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification

from .. import models
from ..tests.test_views import AbstractSuggestedCorrectionAdditionTest


class TestCorrectionStatCounting(AbstractSuggestedCorrectionAdditionTest):
    """
    Run tests to ensure that the notification and stat counts for corrections.
    """

    def test_correction_creation(self):
        self.gamer1.refresh_from_db()
        previous_correction_count = self.gamer1.submitted_corrections
        previous_notification_count = Notification.objects.filter(
            recipient=self.gamer2.user
        ).count()
        self.gamer1.refresh_from_db()
        models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        assert self.gamer1.submitted_corrections - previous_correction_count == 1
        assert (
            Notification.objects.filter(recipient=self.gamer2.user).count()
            - previous_notification_count
            == 1
        )

    def test_new_to_approved(self):
        self.gamer1.refresh_from_db()
        correction = models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        previous_correction_approved = self.gamer1.submitted_corrections_approved
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        correction.status = "approved"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_corrections_approved - previous_correction_approved
            == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )

    def test_new_to_rejected(self):
        self.gamer1.refresh_from_db()
        correction = models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        previous_correction_rejected = self.gamer1.submitted_corrections_rejected
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        correction.status = "rejected"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_corrections_rejected - previous_correction_rejected
            == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )

    def test_approved_to_new(self):
        self.gamer1.refresh_from_db()
        correction = models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        correction.status = "approved"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        previous_correction_approved = self.gamer1.submitted_corrections_approved
        previous_correction_rejected = self.gamer1.submitted_corrections_rejected
        correction.status = "new"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        assert (
            previous_correction_approved - self.gamer1.submitted_corrections_approved
            == 1
        )
        assert (
            self.gamer1.submitted_corrections_rejected == previous_correction_rejected
        )

    def test_rejected_to_new(self):
        self.gamer1.refresh_from_db()
        correction = models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        correction.status = "rejected"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        previous_correction_approved = self.gamer1.submitted_corrections_approved
        previous_correction_rejected = self.gamer1.submitted_corrections_rejected
        correction.status = "new"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_corrections_approved == previous_correction_approved
        )
        assert (
            previous_correction_rejected - self.gamer1.submitted_corrections_rejected
            == 1
        )

    def test_approved_to_rejected(self):
        self.gamer1.refresh_from_db()
        correction = models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        correction.status = "approved"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        previous_correction_approved = self.gamer1.submitted_corrections_approved
        previous_correction_rejected = self.gamer1.submitted_corrections_rejected
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        correction.status = "rejected"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        assert (
            previous_correction_approved - self.gamer1.submitted_corrections_approved
            == 1
        )
        assert (
            self.gamer1.submitted_corrections_rejected - previous_correction_rejected
            == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )

    def test_rejected_to_approved(self):
        self.gamer1.refresh_from_db()
        correction = models.SuggestedCorrection.objects.create(
            submitter=self.gamer1.user,
            content_object=self.cypher,
            new_title="OG Cypher",
            new_description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        correction.status = "rejected"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        previous_correction_approved = self.gamer1.submitted_corrections_approved
        previous_correction_rejected = self.gamer1.submitted_corrections_rejected
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        correction.status = "approved"
        correction.reviewer = self.gamer2.user
        correction.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_corrections_approved - previous_correction_approved
            == 1
        )
        assert (
            previous_correction_rejected - self.gamer1.submitted_corrections_rejected
            == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )


class TestAdditionStatCalcs(AbstractSuggestedCorrectionAdditionTest):
    """
    Test the stat calculations with additions.
    """

    def setUp(self):
        super().setUp()
        self.ct = ContentType.objects.get_for_model(models.GamePublisher)

    def test_addition_creation(self):
        self.gamer1.refresh_from_db()
        previous_additions_count = self.gamer1.submitted_additions
        previous_notification_count = Notification.objects.filter(
            recipient=self.gamer2.user
        ).count()
        self.gamer1.refresh_from_db()
        models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        assert self.gamer1.submitted_additions - previous_additions_count == 1
        assert (
            Notification.objects.filter(recipient=self.gamer2.user).count()
            - previous_notification_count
            == 1
        )

    def test_new_to_approved(self):
        self.gamer1.refresh_from_db()
        addition = models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        previous_addition_approved = self.gamer1.submitted_additions_approved
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        addition.status = "approved"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_additions_approved - previous_addition_approved == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )

    def test_new_to_rejected(self):
        self.gamer1.refresh_from_db()
        addition = models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        previous_addition_rejected = self.gamer1.submitted_additions_rejected
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        addition.status = "rejected"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_additions_rejected - previous_addition_rejected == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )

    def test_approved_to_new(self):
        self.gamer1.refresh_from_db()
        addition = models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        addition.status = "approved"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        previous_addition_approved = self.gamer1.submitted_additions_approved
        previous_addition_rejected = self.gamer1.submitted_additions_rejected
        addition.status = "new"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        assert (
            previous_addition_approved - self.gamer1.submitted_additions_approved == 1
        )
        assert self.gamer1.submitted_additions_rejected == previous_addition_rejected

    def test_rejected_to_new(self):
        self.gamer1.refresh_from_db()
        addition = models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        addition.status = "rejected"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        previous_addition_approved = self.gamer1.submitted_additions_approved
        previous_addition_rejected = self.gamer1.submitted_additions_rejected
        addition.status = "new"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        assert self.gamer1.submitted_additions_approved == previous_addition_approved
        assert (
            previous_addition_rejected - self.gamer1.submitted_additions_rejected == 1
        )

    def test_approved_to_rejected(self):
        self.gamer1.refresh_from_db()
        addition = models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        addition.status = "approved"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        previous_addition_approved = self.gamer1.submitted_additions_approved
        previous_addition_rejected = self.gamer1.submitted_additions_rejected
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        addition.status = "rejected"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        assert (
            previous_addition_approved - self.gamer1.submitted_additions_approved == 1
        )
        assert (
            self.gamer1.submitted_additions_rejected - previous_addition_rejected == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )

    def test_rejected_to_approved(self):
        self.gamer1.refresh_from_db()
        addition = models.SuggestedAddition.objects.create(
            submitter=self.gamer1.user,
            content_type=self.ct,
            title="Andrlik Pub",
            description="The orginal gangsta",
        )
        self.gamer1.refresh_from_db()
        addition.status = "rejected"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        previous_addition_approved = self.gamer1.submitted_additions_approved
        previous_addition_rejected = self.gamer1.submitted_additions_rejected
        previous_user_notifications = Notification.objects.filter(
            recipient=self.gamer1.user
        ).count()
        addition.status = "approved"
        addition.reviewer = self.gamer2.user
        addition.save()
        self.gamer1.refresh_from_db()
        assert (
            self.gamer1.submitted_additions_approved - previous_addition_approved == 1
        )
        assert (
            previous_addition_rejected - self.gamer1.submitted_additions_rejected == 1
        )
        assert (
            Notification.objects.filter(recipient=self.gamer1.user).count()
            - previous_user_notifications
            == 1
        )
