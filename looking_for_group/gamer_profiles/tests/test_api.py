import pytest
from django.urls import reverse

from .. import models

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "gamertouse,viewname,expected_get_response",
    [
        (None, "api-community-list", 403),
        ("gamer1", "api-community-list", 200),
        (None, "api-profile-list", 403),
        ("gamer1", "api-profile-list", 200),
    ],
)
def test_top_list_views(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    viewname,
    expected_get_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    url = reverse(viewname, kwargs={"format": "json"})
    with django_assert_max_num_queries(70):
        response = apiclient.get(url)
    assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamertouse,viewname,communitytouse,expected_get_response",
    [
        (None, "api-member-list", "community1", 403),
        ("gamer1", "api-member-list", "community1", 200),
        ("gamer5", "api-member-list", "community1", 404),
        (None, "api-community-admins", "community1", 403),
        ("gamer1", "api-community-admins", "community1", 200),
        ("gamer5", "api-community-admins", "community1", 403),
        (None, "api-community-mods", "community1", 403),
        ("gamer1", "api-community-mods", "community1", 200),
        ("gamer5", "api-community-mods", "community1", 403),
        (None, "api-community-bans", "community1", 403),
        ("gamer1", "api-community-bans", "community1", 200),
        ("gamer5", "api-community-bans", "community1", 403),
        (None, "api-community-kicks", "community1", 403),
        ("gamer1", "api-community-kicks", "community1", 200),
        ("gamer1", "api-community-kicks", "community1", 403),
        (None, "api-comm-application-list", "community1", 403),
        ("gamer1", "api-comm-application-list", "community1", 200),
        ("gamer5", "api-comm-application-list", "community1", 403),
    ],
)
def test_community_sublists(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    viewname,
    communitytouse,
    expected_get_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata, communitytouse)
    url = reverse(viewname, kwargs={"parent_lookup_community": community.pk})
    with django_assert_max_num_queries(50):
        response = apiclient.get(url)
    assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamertouse,viewname,object_to_use,expected_get_response",
    [
        (None, "api-community-detail", "community1", 403),
        (None, "api-profile-detail", "gamer1", 403),
        ("gamer1", "api-community-detail", "community1", 200),
        ("gamer5", "api-community-detail", "community1", 200),
        ("gamer1", "api-profile-detail", "gamer1", 200),
        ("blocked_gamer", "api-profile-detail", "gamer1", 404),
    ],
)
def test_top_detail_views(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    viewname,
    object_to_use,
    expected_get_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    obj = getattr(social_testdata, object_to_use)
    if isinstance(obj, models.GamerProfile):
        for gamecheck in models.GamerProfile.objects.all():
            print("{}: {}".format(gamecheck.username, gamecheck.pk))
    url = reverse(viewname, kwargs={"format": "json", "pk": obj.pk})
    with django_assert_max_num_queries(70):
        response = apiclient.get(url)
    assert response.status_code == expected_get_response
