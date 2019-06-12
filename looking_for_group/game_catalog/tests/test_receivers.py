import pytest
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification

from .. import models

pytestmark = pytest.mark.django_db(transaction=True)


def test_correction_creation(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_count = catalog_testdata.gamer1.submitted_corrections
    previous_notification_count = Notification.objects.filter(
        recipient=catalog_testdata.gamer2.user
    ).count()
    catalog_testdata.gamer1.refresh_from_db()
    models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_corrections - previous_correction_count == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer2.user).count()
        - previous_notification_count
        == 1
    )


def test_correction_new_to_approved(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    correction = models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_approved = (
        catalog_testdata.gamer1.submitted_corrections_approved
    )
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    correction.status = "approved"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_corrections_approved
        - previous_correction_approved
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


def test_correction_new_to_rejected(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    correction = models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_rejected = (
        catalog_testdata.gamer1.submitted_corrections_rejected
    )
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    correction.status = "rejected"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_corrections_rejected
        - previous_correction_rejected
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


def test_correction_approved_to_new(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    correction = models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    correction.status = "approved"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_approved = (
        catalog_testdata.gamer1.submitted_corrections_approved
    )
    previous_correction_rejected = (
        catalog_testdata.gamer1.submitted_corrections_rejected
    )
    correction.status = "new"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        previous_correction_approved
        - catalog_testdata.gamer1.submitted_corrections_approved
        == 1
    )
    assert (
        catalog_testdata.gamer1.submitted_corrections_rejected
        == previous_correction_rejected
    )


def test_correction_rejected_to_new(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    correction = models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    correction.status = "rejected"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_approved = (
        catalog_testdata.gamer1.submitted_corrections_approved
    )
    previous_correction_rejected = (
        catalog_testdata.gamer1.submitted_corrections_rejected
    )
    correction.status = "new"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_corrections_approved
        == previous_correction_approved
    )
    assert (
        previous_correction_rejected
        - catalog_testdata.gamer1.submitted_corrections_rejected
        == 1
    )


def test_correction_approved_to_rejected(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    correction = models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    correction.status = "approved"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_approved = (
        catalog_testdata.gamer1.submitted_corrections_approved
    )
    previous_correction_rejected = (
        catalog_testdata.gamer1.submitted_corrections_rejected
    )
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    correction.status = "rejected"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        previous_correction_approved
        - catalog_testdata.gamer1.submitted_corrections_approved
        == 1
    )
    assert (
        catalog_testdata.gamer1.submitted_corrections_rejected
        - previous_correction_rejected
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


def test_correction_rejected_to_approved(catalog_testdata):
    catalog_testdata.gamer1.refresh_from_db()
    correction = models.SuggestedCorrection.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_object=catalog_testdata.cypher,
        new_title="OG Cypher",
        new_description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    correction.status = "rejected"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_correction_approved = (
        catalog_testdata.gamer1.submitted_corrections_approved
    )
    previous_correction_rejected = (
        catalog_testdata.gamer1.submitted_corrections_rejected
    )
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    correction.status = "approved"
    correction.reviewer = catalog_testdata.gamer2.user
    correction.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_corrections_approved
        - previous_correction_approved
        == 1
    )
    assert (
        previous_correction_rejected
        - catalog_testdata.gamer1.submitted_corrections_rejected
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


@pytest.fixture
def testing_catalog_ct(catalog_testdata):
    return ContentType.objects.get_for_model(models.GamePublisher)


def test_addition_creation(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    previous_additions_count = catalog_testdata.gamer1.submitted_additions
    previous_notification_count = Notification.objects.filter(
        recipient=catalog_testdata.gamer2.user
    ).count()
    catalog_testdata.gamer1.refresh_from_db()
    models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    assert catalog_testdata.gamer1.submitted_additions - previous_additions_count == 1
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer2.user).count()
        - previous_notification_count
        == 1
    )


def test_addition_new_to_approved(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    addition = models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    previous_addition_approved = catalog_testdata.gamer1.submitted_additions_approved
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    addition.status = "approved"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_additions_approved
        - previous_addition_approved
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


def test_addition_new_to_rejected(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    addition = models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    previous_addition_rejected = catalog_testdata.gamer1.submitted_additions_rejected
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    addition.status = "rejected"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_additions_rejected
        - previous_addition_rejected
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


def test_addition_approved_to_new(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    addition = models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    addition.status = "approved"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_addition_approved = catalog_testdata.gamer1.submitted_additions_approved
    previous_addition_rejected = catalog_testdata.gamer1.submitted_additions_rejected
    addition.status = "new"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        previous_addition_approved
        - catalog_testdata.gamer1.submitted_additions_approved
        == 1
    )
    assert (
        catalog_testdata.gamer1.submitted_additions_rejected
        == previous_addition_rejected
    )


def test_addition_rejected_to_new(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    addition = models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    addition.status = "rejected"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_addition_approved = catalog_testdata.gamer1.submitted_additions_approved
    previous_addition_rejected = catalog_testdata.gamer1.submitted_additions_rejected
    addition.status = "new"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_additions_approved
        == previous_addition_approved
    )
    assert (
        previous_addition_rejected
        - catalog_testdata.gamer1.submitted_additions_rejected
        == 1
    )


def test_addition_approved_to_rejected(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    addition = models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    addition.status = "approved"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_addition_approved = catalog_testdata.gamer1.submitted_additions_approved
    previous_addition_rejected = catalog_testdata.gamer1.submitted_additions_rejected
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    addition.status = "rejected"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        previous_addition_approved
        - catalog_testdata.gamer1.submitted_additions_approved
        == 1
    )
    assert (
        catalog_testdata.gamer1.submitted_additions_rejected
        - previous_addition_rejected
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )


def test_addition_rejected_to_approved(catalog_testdata, testing_catalog_ct):
    catalog_testdata.gamer1.refresh_from_db()
    addition = models.SuggestedAddition.objects.create(
        submitter=catalog_testdata.gamer1.user,
        content_type=testing_catalog_ct,
        title="Andrlik Pub",
        description="The orginal gangsta",
    )
    catalog_testdata.gamer1.refresh_from_db()
    addition.status = "rejected"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    previous_addition_approved = catalog_testdata.gamer1.submitted_additions_approved
    previous_addition_rejected = catalog_testdata.gamer1.submitted_additions_rejected
    previous_user_notifications = Notification.objects.filter(
        recipient=catalog_testdata.gamer1.user
    ).count()
    addition.status = "approved"
    addition.reviewer = catalog_testdata.gamer2.user
    addition.save()
    catalog_testdata.gamer1.refresh_from_db()
    assert (
        catalog_testdata.gamer1.submitted_additions_approved
        - previous_addition_approved
        == 1
    )
    assert (
        previous_addition_rejected
        - catalog_testdata.gamer1.submitted_additions_rejected
        == 1
    )
    assert (
        Notification.objects.filter(recipient=catalog_testdata.gamer1.user).count()
        - previous_user_notifications
        == 1
    )
