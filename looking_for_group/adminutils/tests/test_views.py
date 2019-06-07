import pytest
from django.urls import reverse

from ..views import get_filtered_user_queryset

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "filter_type, filter_mode, expected_result",
    [
        ([], "any", 5),  # Find everyone
        (
            ["notification_digest", "feedback_volunteer"],
            "any",
            2,
        ),  # Find users with either selected
        (
            ["notification_digest", "feedback_volunteer"],
            "all",
            0,
        ),  # Find users with both selected
        (
            ["notification_digest", "feedback_volunteer"],
            "none",
            3,
        ),  # Find users where neither is selected.
    ],
)
def test_filtering(admin_testdata, filter_type, filter_mode, expected_result):
    assert (
        get_filtered_user_queryset(filter_type, filter_mode).count() == expected_result
    )


@pytest.mark.parametrize(
    "view_name, gamer_to_use, expected_status_code, expected_location",
    [
        ("adminutils:notification", None, 302, "/accounts/login/"),  # Must be logged in
        ("adminutils:email", None, 302, "/accounts/login/"),  # Must be logged in
        ("adminutils:notification", "gamer1", 403, None),  # Must be an admin
        ("adminutils:email", "gamer1", 403, None),  # Must be an admin
        ("adminutils:notification", "admin_gamer", 200, None),  # Admin can access
        ("adminutils:email", "admin_gamer", 200, None),  # Admin can access
    ],
)
def test_get_views(
    client,
    django_assert_max_num_queries,
    admin_testdata,
    view_name,
    gamer_to_use,
    expected_status_code,
    expected_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(admin_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse(view_name))
    assert response.status_code == expected_status_code
    if expected_location:
        assert expected_location in response["Location"]


@pytest.mark.parametrize(
    "view_name, data_to_send",
    [
        (
            "adminutils:notification",
            {
                "message": "Hello, friend",
                "filter_options": ["feedback_volunteer"],
                "filter_mode": "any",
            },
        ),
        (
            "adminutils:email",
            {
                "subject": "Greetings",
                "body": "Do you have the time?",
                "filter_options": ["feedback_volunteer"],
                "filter_mode": "any",
            },
        ),
    ],
)
def test_sending_messages(client, admin_testdata, view_name, data_to_send):
    client.force_login(user=admin_testdata.admin_gamer.user)
    response = client.post(reverse(view_name), data=data_to_send)
    assert response.status_code == 302
