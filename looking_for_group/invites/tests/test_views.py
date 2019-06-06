import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from ...gamer_profiles.models import CommunityMembership
from ...games.models import GamePosting, Player
from ..models import Invite

# -------- Start pytest conversions ---------#
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "view_name_to_test",
    ["invites:invite_create", "invites:invite_accept", "invites:invite_delete"],
)
def test_login_required(client, invite_testdata, view_name_to_test):
    if "create" in view_name_to_test:
        url = reverse(view_name_to_test, kwargs=invite_testdata.mem_url_kwargs)
    else:
        url = reverse(
            view_name_to_test, kwargs={"invite": invite_testdata.invite1.slug}
        )
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.parametrize(
    "objtoget, gamer_to_use",
    [("comm3", "gamer1"), ("comm3", "gamer4"), ("gp1", "gamer1")],
)
def test_invite_creation_not_allowed(client, invite_testdata, objtoget, gamer_to_use):
    client.force_login(user=getattr(invite_testdata, gamer_to_use).user)
    obj = getattr(invite_testdata, objtoget)
    response = client.get(
        reverse(
            "invites:invite_create",
            kwargs={
                "content_type": ContentType.objects.get_for_model(obj).pk,
                "slug": obj.slug,
            },
        )
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "objtoget, gamer_to_use",
    [
        ("comm3", "gamer3"),
        ("comm2", "gamer2"),
        ("comm2", "gamer4"),
        ("comm1", "gamer3"),
        ("gp1", "gamer3"),
    ],
)
def test_invite_creation_allowed(
    client, django_assert_max_num_queries, invite_testdata, objtoget, gamer_to_use
):
    client.force_login(user=getattr(invite_testdata, gamer_to_use).user)
    obj = getattr(invite_testdata, objtoget)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "invites:invite_create",
                kwargs={
                    "content_type": ContentType.objects.get_for_model(obj).pk,
                    "slug": obj.slug,
                },
            )
        )
        assert response.status_code == 200


@pytest.mark.parametrize(
    "objtoget,gamer_to_use",
    [
        ("comm3", "gamer3"),
        ("comm2", "gamer2"),
        ("comm2", "gamer4"),
        ("comm1", "gamer3"),
        ("gp1", "gamer3"),
    ],
)
def test_invite_creation(client, invite_testdata, objtoget, gamer_to_use):
    client.force_login(user=getattr(invite_testdata, gamer_to_use).user)
    obj = getattr(invite_testdata, objtoget)
    invite_count = Invite.objects.count()
    response = client.post(
        reverse(
            "invites:invite_create",
            kwargs={
                "content_type": ContentType.objects.get_for_model(obj).pk,
                "slug": obj.slug,
            },
        ),
        data={"label": "Test invite"},
    )
    assert response.status_code == 302
    assert Invite.objects.count() - invite_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, invite_to_use", [("gamer2", "invite1"), ("gamer3", "invite3")]
)
def test_deletion_not_allowed(client, invite_testdata, gamer_to_use, invite_to_use):
    client.force_login(user=getattr(invite_testdata, gamer_to_use).user)
    invite = getattr(invite_testdata, invite_to_use)
    response = client.get(
        reverse("invites:invite_delete", kwargs={"invite": invite.slug})
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "gamer_to_use, invite_to_use",
    [("gamer3", "invite1"), ("gamer1", "invite2"), ("gamer1", "invite3")],
)
def test_delete_invite(
    client, django_assert_max_num_queries, invite_testdata, gamer_to_use, invite_to_use
):
    client.force_login(user=getattr(invite_testdata, gamer_to_use).user)
    invite = getattr(invite_testdata, invite_to_use)
    url = reverse("invites:invite_delete", kwargs={"invite": invite.slug})
    invite_count = Invite.objects.count()
    with django_assert_max_num_queries(50):
        response = client.get(url)
    assert response.status_code == 200
    response = client.post(url, data={})
    assert response.status_code == 302
    assert invite_count - Invite.objects.count() == 1


@pytest.mark.parametrize(
    "gamer_to_use, invite_to_use, expected_get_status, data_to_send, expected_result",
    [
        ("gamer5", "expired_invite", 302, {}, "expired"),
        ("gamer5", "invite1", 200, {"status": "accepted"}, "accepted"),
        ("gamer5", "accepted_invite", 302, {"status": "accepted"}, "accepted"),
        ("gamer5", "invite1", 200, {"status": "expired"}, "pending"),
        ("gamer2", "invite3", 200, {"status": "accepted"}, "accepted"),
        ("gamer4", "invite2", 200, {"status": "accepted"}, "accepted"),
    ],
)
def test_invite_acceptance(
    client,
    django_assert_max_num_queries,
    invite_testdata,
    gamer_to_use,
    invite_to_use,
    expected_get_status,
    data_to_send,
    expected_result,
):
    gamer = getattr(invite_testdata, gamer_to_use)
    client.force_login(user=gamer.user)
    invite = getattr(invite_testdata, invite_to_use)
    url = reverse("invites:invite_accept", kwargs={"invite": invite.slug})
    with django_assert_max_num_queries(50):
        response = client.get(url)
        assert response.status_code == expected_get_status
    if expected_get_status == 200:
        response = client.post(url, data=data_to_send)
        assert Invite.objects.get(pk=invite.pk).status == expected_result
        if expected_result == "pending":
            assert response.status_code == 200
        else:
            assert response.status_code == 302
            assert Invite.objects.get(pk=invite.pk).accepted_by == gamer.user
            if isinstance(invite.content_object, GamePosting):
                assert Player.objects.get(gamer=gamer, game=invite.content_object)
            else:
                assert CommunityMembership.objects.get(
                    gamer=gamer, community=invite.content_object
                )
