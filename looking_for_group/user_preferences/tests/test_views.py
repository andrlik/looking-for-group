import pytest
from django.urls import reverse

from ...gamer_profiles import models as social_models
from ..models import Preferences
from ..utils import fetch_or_set_discord_comm_links, prime_site_stats_cache

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "view_name, gamer_to_use, expected_status_code, expected_location",
    [
        (
            "user_preferences:setting-view",
            None,
            302,
            "/accounts/login/",
        ),  # Require login
        (
            "user_preferences:setting-edit",
            None,
            302,
            "/accounts/login/",
        ),  # Require login
        ("dashboard", None, 302, "/accounts/login/"),  # Require login
        (
            "user_preferences:account_delete",
            None,
            302,
            "/accounts/login/",
        ),  # Require login
        ("user_preferences:setting-view", "gamer1", 200, None),  # Valid
        ("user_preferences:setting-edit", "gamer1", 200, None),  # Valid
        ("dashboard", "gamer1", 200, None),  # Valid
        ("user_preferences:account_delete", "gamer1", 200, None),  # Valid
    ],
)
def test_get_requests(
    client,
    game_testdata,
    django_assert_max_num_queries,
    view_name,
    gamer_to_use,
    expected_status_code,
    expected_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse(view_name))
    assert response.status_code == expected_status_code
    if expected_location:
        assert expected_location in response["Location"]


def test_update_settings(client, game_testdata):
    client.force_login(user=game_testdata.gamer1.user)
    response = client.post(
        reverse("user_preferences:setting-edit"),
        data={"news_emails": 1, "notification_digest": 1, "feedback_volunteer": 1},
    )
    assert response.status_code == 302
    new_version = Preferences.objects.get(gamer=game_testdata.gamer1)
    assert (
        new_version.news_emails
        and new_version.notification_digest
        and new_version.feedback_volunteer
    )


def test_delete_requires_confirm_code(client, game_testdata):
    client.force_login(user=game_testdata.gamer1.user)
    response = client.post(reverse("user_preferences:account_delete"), data={})
    assert response.status_code == 200
    assert social_models.GamerProfile.objects.get(pk=game_testdata.gamer1.pk)


# Check that our cache and fetch methods don't generate exceptions


def test_discord_fetch(game_testdata):
    fetch_or_set_discord_comm_links()


def test_stats_priming(game_testdata):
    prime_site_stats_cache()
