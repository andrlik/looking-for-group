import pytest
from allauth.account.signals import user_logged_in
from django.test import RequestFactory
from django.urls import reverse
from factory.django import mute_signals

from ..models import ReleaseNote, ReleaseNotice
from ..serializers import ReleaseNoteSerializer
from ..signals import user_specific_notes_displayed

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("gamertouse", [None, "gamer1", "gamer2"])
def test_release_note_details_view(
    client, django_assert_max_num_queries, rn_testdata, gamertouse
):
    """
    Test the basic release notes display.
    """
    gamer = None
    if gamertouse:
        gamer = getattr(rn_testdata, gamertouse)
        client.force_login(gamer.user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse("releasenotes:note-list"))
    assert response.status_code == 200
    assert len(response.context["rn_list"]) == ReleaseNote.objects.count()


@pytest.mark.parametrize("gamertouse", [None, "gamer1", "gamer2"])
def test_release_notes_json_view(
    apiclient, django_assert_max_num_queries, rn_testdata, gamertouse
):
    """
    Test the JSON version of the release notes view.
    """
    gamer = None
    if gamertouse:
        gamer = getattr(rn_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    with django_assert_max_num_queries(50):
        response = apiclient.get(reverse("releasenotes:note-list-json"))
    # print(response.data)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "gamertouse,expected_get_response,expected_get_location,expected_note_count",
    [
        (None, 302, "accounts/login", 0),
        ("gamer1", 200, None, 0),
        ("gamer2", 200, None, 3),
    ],
)
def test_release_note_context(
    client,
    django_assert_max_num_queries,
    rn_testdata,
    gamertouse,
    expected_get_response,
    expected_get_location,
    expected_note_count,
):
    """
    Test that we are querying the release notes to show correctly.
    """
    gamer = None
    if gamertouse:
        gamer = getattr(rn_testdata, gamertouse)
        notice = getattr(rn_testdata, "gn{}".format(gamertouse[-1]))
        client.force_login(gamer.user)
        with mute_signals(user_specific_notes_displayed):
            user_logged_in.send(
                sender=type(gamer.user),
                instance=gamer.user,
                user=gamer.user,
                request=client.get("/").wsgi_request,
            )
    with django_assert_max_num_queries(50):
        response = client.get(reverse("gamer_profiles:my-community-list"))
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    else:
        notice.refresh_from_db()
        assert notice.latest_version_shown == ReleaseNote.objects.latest("release_date")
