from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone

from ...invites.models import Invite
from .. import models
from . import factories

pytestmark = pytest.mark.django_db(transaction=True)


def test_setup_variables(social_testdata):
    assert social_testdata.community1.get_role(social_testdata.gamer1) == "Admin"
    assert social_testdata.community2.get_role(social_testdata.gamer2) == "Member"
    assert social_testdata.gamer1 in social_testdata.gamer3.friends.all()


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location, change_expected",
    [
        (None, 302, "/accounts/login", False),
        ("gamer2", 405, None, False),
        ("gamer1", 405, None, True),
    ],
)
def test_toggle_notifications_view(
    client,
    social_testdata,
    gamer_to_use,
    expected_get_response,
    expected_get_location,
    change_expected,
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse(
        "gamer_profiles:community-toggle-notifications",
        kwargs={"community": social_testdata.community1.slug},
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    else:
        if change_expected:
            response = client.post(url, data={})
            assert response.status_code == 302
            assert models.CommunityMembership.objects.get(
                gamer=gamer, community=social_testdata.community1
            ).game_notifications
        else:
            response = client.post(url, data={}, follow=True)
            assert response.status_code == 200
            messages = list(response.context["messages"])
            assert "error" in messages[0].tags


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [(None, 302, "/accounts/login/"), ("gamer1", 200, None)],
)
def test_create_community(
    client, social_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    """
    Test community creation views.
    """
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse("gamer_profiles:community-create")
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        post_data = {
            "name": "My cool new community",
            "description": "We play fun games.",
            "url": "",
            "private": "",
            "application_approval": "admin",
            "invites_allowed": "admin",
        }
        prev_count = models.GamerCommunity.objects.count()
        response = client.post(url, data=post_data)
        assert response.status_code == 302
        assert models.GamerCommunity.objects.count() - prev_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, expected_text, expected_not_text",
    [
        (None, None, None),
        ("gamer2", [b"<span class='membership label secondary'>Member</span>"], None),
        ("gamer1", [b"<span class='membership label primary'>Admin</span>"], None),
        (
            "gamer3",
            [b"class='button small'>Apply", b"class='button small'>Apply"],
            b"<span class='membership'>",
        ),
    ],
)
def test_comm_List_view(
    client,
    social_testdata,
    django_assert_max_num_queries,
    gamer_to_use,
    expected_text,
    expected_not_text,
):
    """
    Try loading the list view for various uses and test that the controls for each one are rendered correctly.
    """
    if gamer_to_use:
        client.force_login(getattr(social_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse("gamer_profiles:community-list"))
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 4
    if expected_text:
        for text in expected_text:
            print("Checking for {}".format(text))
            assert text in response.content
    if expected_not_text:
        assert expected_not_text not in response.content


@pytest.mark.parametrize(
    "gamer_to_use, expected_count", [("gamer1", 3), ("gamer2", 1), ("gamer3", 1)]
)
def test_my_community_list(
    client, social_testdata, django_assert_max_num_queries, gamer_to_use, expected_count
):
    client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    response = client.get(reverse("gamer_profiles:my-community-list"))
    assert response.status_code == 200
    assert len(response.context["object_list"]) == expected_count


@pytest.mark.parametrize(
    "gamer_to_use, comm_to_test, expected_get_response, expected_get_location",
    [
        (None, "community1", 302, "/accounts/login/"),
        ("gamer1", "community1", 200, None),
        ("gamer1", "community2", 200, None),
        ("gamer2", "community1", 302, None),
        ("gamer2", "community2", 200, None),
        ("gamer3", "community1", 302, None),
        ("gamer3", "community2", 200, None),
    ],
)
def test_community_detail_view(
    client,
    social_testdata,
    django_assert_max_num_queries,
    gamer_to_use,
    comm_to_test,
    expected_get_response,
    expected_get_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "gamer_profiles:community-detail",
                kwargs={"community": getattr(social_testdata, comm_to_test).slug},
            )
        )
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [(None, 302, "/accounts/login/"), ("gamer1", 200, None), ("gamer2", 403, None)],
)
def test_community_member_list(
    client,
    social_testdata,
    django_assert_max_num_queries,
    gamer_to_use,
    expected_get_response,
    expected_get_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "gamer_profiles:community-member-list",
                kwargs={"community": social_testdata.community1.slug},
            )
        )
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]


def test_member_list_paginated(client, social_testdata, django_assert_max_num_queries):
    client.force_login(user=social_testdata.gamer1.user)
    url = reverse(
        "gamer_profiles:community-member-list",
        kwargs={"community": social_testdata.community1.slug, "page": 2},
    )
    response = client.get(url)
    assert response.status_code == 404
    for x in range(40):
        tempgamer = factories.GamerProfileFactory()
        social_testdata.community1.add_member(tempgamer)
    with django_assert_max_num_queries(80):
        response = client.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [(None, 302, "/accounts/login/"), ("gamer3", 403, None), ("gamer1", 200, None)],
)
def test_community_edit(
    client, social_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community-edit",
        kwargs={"community": social_testdata.community1.slug},
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        response = client.post(
            url,
            data={
                "name": "Can anyone hear me?",
                "description": "I've been so lost.",
                "url": "https://www.google.com",
                "private": "",
                "application_approval": "admin",
                "invites_allowed": "admin",
            },
        )
        assert response.status_code == 302
        assert (
            models.GamerCommunity.objects.get(pk=social_testdata.community1.pk).name
            == "Can anyone hear me?"
        )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [(None, 302, "/accounts/login/"), ("gamer3", 403, None), ("gamer1", 200, None)],
)
def test_community_delete(
    client, social_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community-delete",
        kwargs={"community": social_testdata.community1.slug},
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        response = client.post(url, data={})
        assert response.status_code == 302
        with pytest.raises(ObjectDoesNotExist):
            models.GamerCommunity.objects.get(pk=social_testdata.community1.pk)


@pytest.mark.parametrize(
    "gamer_to_use, community_to_test, expected_get_response, expected_get_location, expected_post_response, should_join",
    [
        (None, "community1", 302, "/accounts/login/", None, False),
        ("gamer4", "community1", 302, "apply", 302, False),  # Private community
        ("gamer4", "community2", 200, None, 302, True),  # Public community
        ("gamer2", "community2", 302, None, 302, True),  # Already in community
        (
            "gamer3",
            "community2",
            403,
            None,
            403,
            False,
        ),  # Kicked gamer with future expiration
        (
            "gamer2",
            "community1",
            302,
            "apply",
            302,
            False,
        ),  # Kicked gamer whose kick has expired
        ("gamer4", "community", 302, None, 302, False),  # Banned gamer
    ],
)
def test_community_join_view(
    client,
    social_testdata_with_kicks,
    gamer_to_use,
    community_to_test,
    expected_get_response,
    expected_get_location,
    expected_post_response,
    should_join,
):
    gamer = None
    if gamer_to_use:
        gamer = getattr(social_testdata_with_kicks, gamer_to_use)
        client.force_login(user=gamer.user)
    comm = getattr(social_testdata_with_kicks, community_to_test)
    url = reverse("gamer_profiles:community-join", kwargs={"community": comm.slug})
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if gamer:
        response = client.post(url, data={"confirm": "confirm"})
        assert response.status_code == expected_post_response
        if not should_join:
            with pytest.raises(models.NotInCommunity):
                comm.get_role(gamer)
        else:
            assert comm.get_role(gamer)


@pytest.mark.parametrize(
    "gamer_to_use, gamer_to_update, expected_get_response, should_update",
    [
        (None, "gamer2", 302, False),
        ("gamer3", "gamer2", 403, False),
        ("gamer1", "gamer1", 403, False),
        ("gamer5", "gamer2", 200, True),
    ],
)
def test_community_change_role(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    gamer_to_update,
    expected_get_response,
    should_update,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community-edit-gamer-role",
        kwargs={
            "community": social_testdata.community2.slug,
            "gamer": social_testdata.gamer2.username,
        },
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={"community_role": "admin"})
        if should_update:
            assert (
                social_testdata.community2.get_role(social_testdata.gamer2) == "Admin"
            )
        else:
            assert (
                social_testdata.community2.get_role(social_testdata.gamer2) != "Admin"
            )


@pytest.mark.parametrize(
    "gamer_to_use, community_to_use, expected_get_response, should_submit, should_succeed",
    [
        (None, "community1", 302, False, False),
        ("gamer2", "community1", 200, False, True),  # Kicked user without a suspension
        ("gamer3", "community1", 403, False, False),  # Suspended user
        ("gamer4", "community", 403, False, False),  # banned user
        ("gamer5", "community1", 200, False, True),  # Normal user without submit
        ("gamer5", "community1", 200, True, True),  # Normal user with submit.
    ],
)
def test_community_apply_view(
    client,
    social_testdata_with_kicks,
    assert_login_redirect,
    gamer_to_use,
    community_to_use,
    expected_get_response,
    should_submit,
    should_succeed,
):
    gamer = None
    if gamer_to_use:
        gamer = getattr(social_testdata_with_kicks, gamer_to_use)
        client.force_login(user=gamer.user)
    comm = getattr(social_testdata_with_kicks, community_to_use)
    url = reverse("gamer_profiles:community-apply", kwargs={"community": comm.slug})
    response = client.get(url)
    if not gamer:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        post_data = {"message": "Hi there"}
        if should_submit:
            post_data["submit_app"] = ""
        response = client.post(url, data=post_data)
        if should_succeed:
            appl = models.CommunityApplication.objects.get(community=comm, gamer=gamer)
            assert appl
            if should_submit:
                assert appl.status == "review"
            else:
                assert appl.status == "new"


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, should_submit, should_succeed",
    [
        (None, 302, False, False),
        ("gamer2", 403, False, False),  # Non application owner
        ("gamer3", 200, False, True),  # Owner without submit
        ("gamer3", 200, True, True),  # Owner with submit.
    ],
)
def test_update_application(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    should_submit,
    should_succeed,
):
    application = models.CommunityApplication.objects.create(
        gamer=social_testdata.gamer3,
        message="Not me",
        community=social_testdata.community1,
        status="new",
    )
    url = reverse(
        "gamer_profiles:update-application", kwargs={"application": application.pk}
    )
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        update_data = {"message": "This is better"}
        if should_submit:
            update_data["submit_app"] = ""
        response = client.post(url, data=update_data)
        appl = models.CommunityApplication.objects.get(pk=application.pk)
        if should_succeed:
            assert appl.message == "This is better"
            if should_submit:
                assert appl.status == "review"
            else:
                assert appl.status == "new"
        else:
            assert appl.message == "Not me"
            assert appl.status == "new"


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, should_succeed",
    [
        (None, 302, False),
        ("gamer2", 403, False),  # Not application owner
        ("gamer3", 200, True),  # Application owner
    ],
)
def test_application_withdrawl(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    should_succeed,
):
    application = models.CommunityApplication.objects.create(
        gamer=social_testdata.gamer3,
        message="Not me",
        community=social_testdata.community1,
        status="new",
    )
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:delete-application", kwargs={"application": application.pk}
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        if should_succeed:
            with pytest.raises(ObjectDoesNotExist):
                models.CommunityApplication.objects.get(pk=application.pk)
        else:
            assert models.CommunityApplication.objects.get(pk=application.pk)


@pytest.mark.parametrize(
    "gamer_to_use, expected_list_response, expected_detail1_response, expected_detail2_response",
    [
        (None, 302, 302, 302),
        ("gamer2", 403, 403, 403),  # Not an admin
        ("gamer1", 200, 200, 403),  # Admin can only see submitted apps
        (
            "gamer3",
            403,
            403,
            403,
        ),  # Owner can't see the details since it's only for review
    ],
)
def test_community_applicant_list_detail(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_list_response,
    expected_detail1_response,
    expected_detail2_response,
):
    application1 = models.CommunityApplication.objects.create(
        gamer=social_testdata.gamer3,
        message="Notice me, Senpai!",
        community=social_testdata.community1,
        status="review",
    )
    application2 = models.CommunityApplication.objects.create(
        gamer=social_testdata.gamer2,
        message="I want to play!",
        community=social_testdata.community1,
        status="new",
    )
    list_url = reverse(
        "gamer_profiles:community-applicant-list",
        kwargs={"community": social_testdata.community1.slug},
    )
    detail1_url = reverse(
        "gamer_profiles:community-applicant-detail",
        kwargs={
            "community": social_testdata.community1.slug,
            "application": application1.pk,
        },
    )
    detail2_url = reverse(
        "gamer_profiles:community-applicant-detail",
        kwargs={
            "community": social_testdata.community1.slug,
            "application": application2.pk,
        },
    )
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    response = client.get(list_url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
        assert assert_login_redirect(client.get(detail1_url))
        assert assert_login_redirect(client.get(detail2_url))
    else:
        assert expected_list_response == response.status_code
        if expected_list_response == 200:
            assert len(response.context["applicants"]) == 1
    response = client.get(detail1_url)
    assert response.status_code == expected_detail1_response
    response = client.get(detail2_url)
    assert response.status_code == expected_detail2_response


@pytest.mark.parametrize(
    "gamer_to_use, application_to_use, view_name, expected_response, expected_status",
    [
        (
            None,
            "application1",
            "gamer_profiles:community-applicant-approve",
            302,
            "review",
        ),  # Login required
        (
            None,
            "application1",
            "gamer_profiles:community-applicant-reject",
            302,
            "review",
        ),  # Login required
        (
            "gamer2",
            "application1",
            "gamer_profiles:community-applicant-approve",
            403,
            "review",
        ),  # Unauthorized
        (
            "gamer2",
            "application1",
            "gamer_profiles:community-applicant-reject",
            403,
            "review",
        ),  # Unauthorized
        (
            "gamer1",
            "application2",
            "gamer_profiles:community-applicant-approve",
            404,
            "new",
        ),  # Authorized but invalid target
        (
            "gamer1",
            "application2",
            "gamer_profiles:community-applicant-reject",
            404,
            "new",
        ),  # Authorized but invalid target
        (
            "gamer1",
            "application1",
            "gamer_profiles:community-applicant-approve",
            302,
            "approve",
        ),  # Authorized but invalid target
        (
            "gamer1",
            "application1",
            "gamer_profiles:community-applicant-reject",
            302,
            "reject",
        ),  # Authorized but invalid target
    ],
)
def test_application_approve_reject(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    application_to_use,
    view_name,
    expected_response,
    expected_status,
):
    previous_member_count = models.CommunityMembership.objects.filter(
        community=social_testdata.community1
    ).count()
    application1 = models.CommunityApplication.objects.create(
        gamer=social_testdata.gamer3,
        message="Notice me, Senpai!",
        community=social_testdata.community1,
        status="review",
    )
    application2 = models.CommunityApplication.objects.create(
        gamer=social_testdata.gamer2,
        message="I want to play!",
        community=social_testdata.community1,
        status="new",
    )
    if application_to_use == "application1":
        pk_to_check = application1.pk
    else:
        pk_to_check = application2.pk
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        view_name,
        kwargs={
            "community": social_testdata.community1.slug,
            "application": pk_to_check,
        },
    )
    response = client.get(url)
    assert response.status_code == 405
    response = client.post(url, data={})
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_response
    assert (
        models.CommunityApplication.objects.get(pk=pk_to_check).status
        == expected_status
    )
    if expected_status == "approve":
        assert (
            models.CommunityMembership.objects.filter(
                community=social_testdata.community1
            ).count()
            - previous_member_count
            == 1
        )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer2", 403), ("gamer1", 200)],
)
def test_kick_list(
    client,
    social_testdata_with_kicks,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata_with_kicks, gamer_to_use).user)
    response = client.get(
        reverse(
            "gamer_profiles:community-kick-list",
            kwargs={"community": social_testdata_with_kicks.community1.slug},
        )
    )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        if expected_get_response == 200:
            assert len(response.context["kick_list"]) == 1
            assert len(response.context["expired_kicks"]) == 1


@pytest.mark.parametrize(
    "gamer_to_use, gamer_to_kick, expected_get_response, post_data, expected_post_response",
    [
        (None, "gamer2", 302, None, None),  # Login required
        (
            "gamer3",
            "gamer2",
            403,
            {
                "reason": "Jerk",
                "end_date": (timezone.now() + timedelta(days=2)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            403,
        ),  # Unauthorized
        (
            "gamer1",
            "gamer3",
            403,
            {
                "end_date": (timezone.now() + timedelta(days=2)).strftime(
                    "%Y-%m-%d %H:%M"
                )
            },
            403,
        ),  # Authorized but invalid target
        (
            "gamer1",
            "gamer2",
            200,
            {
                "reason": "Jerk",
                "end_date": (timezone.now() + timedelta(days=2)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            302,
        ),  # Authorized and valid
    ],
)
def test_kick_user(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    gamer_to_kick,
    expected_get_response,
    post_data,
    expected_post_response,
):
    social_testdata.community1.add_member(social_testdata.gamer2)
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    kickee = getattr(social_testdata, gamer_to_kick)
    url = reverse(
        "gamer_profiles:community-kick-gamer",
        kwargs={"community": social_testdata.community1.slug, "gamer": kickee.username},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        prev_kicks = models.KickedUser.objects.filter(
            community=social_testdata.community1
        ).count()
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.KickedUser.objects.filter(
                    community=social_testdata.community1
                ).count()
                - prev_kicks
                == 1
            )
            with pytest.raises(models.NotInCommunity):
                social_testdata.community1.get_role(kickee)


@pytest.mark.parametrize(
    "gamer_to_use, community_to_use, kick_record_to_use, expected_get_response, post_data, expected_post_response",
    [
        (None, "community1", "kick2", 302, None, None),  # Login required
        (
            "gamer2",
            "community1",
            "kick2",
            403,
            {
                "reason": "Posting adult games without CW",
                "end_date": (timezone.now() + timedelta(days=5)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            403,
        ),  # Unauthorized user
        (
            "gamer2",
            "community2",
            "kick2",
            403,
            {
                "reason": "Posting adult games without CW",
                "end_date": (timezone.now() + timedelta(days=5)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            403,
        ),  # Unauthorized and bad urls
        (
            "gamer1",
            "community2",
            "kick1",
            403,
            {
                "reason": "Posting adult games without CW",
                "end_date": (timezone.now() + timedelta(days=5)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            403,
        ),  # Authorized but with bad url
        (
            "gamer1",
            "community1",
            "kick1",
            403,
            {
                "reason": "Posting adult games without CW",
                "end_date": (timezone.now() + timedelta(days=5)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            403,
        ),  # Authroized but kick already expired
        (
            "gamer1",
            "community1",
            "kick2",
            200,
            {"gamer": "jonathan"},
            200,
        ),  # Authorized but with bad post data
        (
            "gamer1",
            "community1",
            "kick2",
            200,
            {
                "reason": "Posting adult games without CW",
                "end_date": (timezone.now() + timedelta(days=5)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
            302,
        ),  # valid!
    ],
)
def update_kick_record(
    client,
    social_testdata_with_kicks,
    assert_login_redirect,
    gamer_to_use,
    community_to_use,
    kick_record_to_use,
    expected_get_response,
    post_data,
    expected_post_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata_with_kicks, gamer_to_use).user)
    kick_record = getattr(social_testdata_with_kicks, kick_record_to_use)
    community = getattr(social_testdata_with_kicks, community_to_use)
    url = reverse(
        "gamer_profiles:community-kick-edit",
        kwargs={"community": community.slug, "kick": kick_record.pk},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.KickedUser.objects.get(pk=kick_record.pk).reason
                == post_data["reason"]
            )
        else:
            assert (
                models.KickedUser.objects.get(pk=kick_record.pk).reason
                != post_data["reason"]
            )


@pytest.mark.parametrize(
    "gamer_to_use, community_to_use, kick_record_to_use, expected_get_response, expected_post_response",
    [
        (None, "community1", "kick2", 302, None),  # Login required
        ("gamer2", "community1", "kick2", 403, 403),  # Unauthorized user
        ("gamer2", "community2", "kick2", 404, 404),  # Unauthorized and bad urls
        ("gamer1", "community2", "kick1", 404, 404),  # Bad url
        (
            "gamer1",
            "community1",
            "kick1",
            200,
            302,
        ),  # Authorized users can delete an expired kick
        ("gamer1", "community1", "kick2", 200, 302),  # valid!
    ],
)
def test_delete_kick_test(
    client,
    social_testdata_with_kicks,
    assert_login_redirect,
    gamer_to_use,
    community_to_use,
    kick_record_to_use,
    expected_get_response,
    expected_post_response,
):
    kick_record = getattr(social_testdata_with_kicks, kick_record_to_use)
    community = getattr(social_testdata_with_kicks, community_to_use)
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata_with_kicks, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community-kick-delete",
        kwargs={"community": community.slug, "kick": kick_record.pk},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.KickedUser.objects.get(pk=kick_record.pk)
        else:
            assert models.KickedUser.objects.get(pk=kick_record.pk)


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer1", 403), ("gamer5", 200)],
)
def test_ban_list(
    client,
    social_testdata_with_kicks,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata_with_kicks, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "gamer_profiles:community-ban-list",
                kwargs={"community": social_testdata_with_kicks.community.slug},
            )
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        if expected_get_response == 200:
            assert len(response.context["ban_list"]) == 1


@pytest.mark.parametrize(
    "gamer_to_use, gamer_to_ban, community_to_use, expected_get_response, post_data, expected_post_response",
    [
        (None, "gamer1", "community1", 302, None, None),  # Login required
        (
            "gamer3",
            "gamer2",
            "community1",
            403,
            {"reason": "Jerk"},
            403,
        ),  # User not authorized
        (
            "gamer1",
            "gamer5",
            "community1",
            403,
            {"reason": "Jerk"},
            403,
        ),  # User is authorized but target not in community.
        (
            "gamer1",
            "gamer2",
            "community1",
            200,
            {},
            200,
        ),  # User is authorized but post data is bad
        (
            "gamer1",
            "gamer2",
            "community1",
            200,
            {"reason": "Jerk"},
            302,
        ),  # Authroized and valid
    ],
)
def test_ban_user(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    gamer_to_ban,
    community_to_use,
    expected_get_response,
    post_data,
    expected_post_response,
):
    social_testdata.community1.add_member(social_testdata.gamer2)
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    bad_gamer = getattr(social_testdata, gamer_to_ban)
    community = getattr(social_testdata, community_to_use)
    url = reverse(
        "gamer_profiles:community-ban-gamer",
        kwargs={"community": community.slug, "gamer": bad_gamer.username},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, post_data)
        assert response.status_code == expected_post_response
        if response.status_code == 302:
            assert models.BannedUser.objects.get(
                community=community, banned_user=bad_gamer
            )
        else:
            with pytest.raises(ObjectDoesNotExist):
                models.BannedUser.objects.get(
                    community=community, banned_user=bad_gamer
                )


@pytest.mark.parametrize(
    "gamer_to_use, community_to_use, expected_get_response, post_data, expected_post_response",
    [
        (None, "community", 302, None, None),  # Login required
        ("gamer2", "community", 403, {"reason": "He's pure evil"}, 403),  # Unauthorized
        (
            "gamer5",
            "community2",
            404,
            {"reason": "He's pure evil"},
            404,
        ),  # Community mismatch
        ("gamer5", "community", 200, {"gamer": "monkey"}, 200),  # Bad post data
        ("gamer5", "community", 200, {"reason": "He's pure evil"}, 302),  # Valid!
    ],
)
def test_ban_update(
    client,
    social_testdata_with_kicks,
    assert_login_redirect,
    gamer_to_use,
    community_to_use,
    expected_get_response,
    post_data,
    expected_post_response,
):
    community = getattr(social_testdata_with_kicks, community_to_use)
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata_with_kicks, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community-ban-edit",
        kwargs={
            "community": community.slug,
            "ban": social_testdata_with_kicks.banned1.pk,
        },
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.BannedUser.objects.get(
                    pk=social_testdata_with_kicks.banned1.pk
                ).reason
                == post_data["reason"]
            )
        else:
            if "reason" in post_data.keys():
                assert (
                    models.BannedUser.objects.get(
                        pk=social_testdata_with_kicks.banned1.pk
                    ).reason
                    != post_data["reason"]
                )


@pytest.mark.parametrize(
    "gamer_to_use, community_to_use, expected_get_response, expected_post_response",
    [
        (None, "community", 302, None),
        ("gamer1", "community", 403, 403),
        ("gamer5", "community2", 404, 404),
        ("gamer5", "community", 200, 302),
    ],
)
def test_delete_ban(
    client,
    social_testdata_with_kicks,
    assert_login_redirect,
    gamer_to_use,
    community_to_use,
    expected_get_response,
    expected_post_response,
):
    community = getattr(social_testdata_with_kicks, community_to_use)
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata_with_kicks, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community-ban-delete",
        kwargs={
            "community": community.slug,
            "ban": social_testdata_with_kicks.banned1.pk,
        },
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.BannedUser.objects.get(
                    community=social_testdata_with_kicks.community,
                    banned_user=social_testdata_with_kicks.gamer4,
                )
        else:
            assert models.BannedUser.objects.get(
                pk=social_testdata_with_kicks.banned1.pk
            )


@pytest.mark.parametrize(
    "gamer_to_use, gamer_to_view, expected_get_response, expected_get_location",
    [
        (None, "gamer1", 302, None),  # Login required
        ("gamer2", "public_gamer", 200, None),  # Public profile
        ("gamer2", "gamer5", 302, "friend"),  # Public community, not connected
        ("gamer5", "gamer1", 200, None),  # Same private community
        ("gamer2", "gamer1", 302, "friend"),  # Not connected redriect to friend
        (
            "gamer1",
            "gamer6",
            302,
            "friend",
        ),  # A public community doens't count as a personal connection.
        ("gamer3", "gamer1", 200, None),  # Already friends
        ("blocked_gamer", "gamer1", 403, None),  # Blocked
    ],
)
def test_gamer_profile_detail(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    gamer_to_view,
    expected_get_response,
    expected_get_location,
):
    gamer_target = getattr(social_testdata, gamer_to_view)
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:profile-detail", kwargs={"gamer": gamer_target.username}
    )
    with django_assert_max_num_queries(80):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        if expected_get_location:
            assert expected_get_location in response["Location"]


@pytest.mark.parametrize(
    "gamer_to_use, post_data_key, expected_post_response",
    [
        (None, None, None),  # Login required
        ("gamer1", "invalid_user_post", 200),  # Invalid data in the user form
        ("gamer1", "invalid_profile_post", 200),  # Invalid data in the profile form
        ("gamer1", "valid_post", 302),  # Valid!
    ],
)
def test_profile_update(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    post_data_key,
    expected_post_response,
):
    post_data_dict = {
        "valid_post": {
            "display_name": "Charles",
            "bio": "Born in the USA",
            "homepage_url": "https://www.google.com",
            "profile-private": 1,
            "profile-rpg_experience": "I dabble",
            "profile-ttg_experience": "A few rounds of Catan",
            "profile-player_status": "searching",
            "profile-one_shots": 1,
            "profile-online_games": 1,
        },
        "invalid_user_post": {
            "display_name": "Charles",
            "bio": """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras ipsum nibh, tempus et feugiat sit amet, egestas tincidunt tortor. Fusce pellentesque laoreet ultrices. Proin luctus ullamcorper erat, in rhoncus ipsum semper sit amet. Suspendisse felis risus, placerat a semper sed, commodo eu velit. Sed feugiat venenatis ultricies. Vivamus ullamcorper, leo eget mollis mollis, libero nisl pulvinar nisi, non pharetra nulla odio vitae purus. Pellentesque et libero eros, sed tincidunt ligula. Phasellus id metus justo. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Ut mollis tincidunt bibendum.

Pellentesque faucibus, risus eu mattis viverra, tortor tellus lobortis nibh, vel suscipit justo odio euismod mauris. Etiam consectetur, lorem sit amet iaculis rhoncus, nulla sapien dictum erat, id eleifend ligula neque congue sapien. Proin in posuere risus. Nullam porttitor venenatis velit, id malesuada urna egestas eget. Praesent eget turpis vitae elit suscipit luctus et vel lectus. Etiam sapien nulla, imperdiet porta accumsan in, facilisis et lacus. Etiam risus dui, ornare eget fringilla eget, consequat vel odio. Nam diam leo, lacinia sit amet sagittis vel, blandit nec felis. Pellentesque mattis malesuada orci, ac lobortis lacus pellentesque sit amet. Morbi tempus diam eu quam luctus tempor. Mauris pretium, lectus id elementum faucibus, turpis urna dignissim metus, eu viverra nibh purus id nisi. Nunc id nunc quam. Suspendisse vitae lacus nisl, vel placerat libero. Donec dui enim, congue ac dictum id, ullamcorper sit amet elit. Maecenas nunc purus, viverra id placerat vitae, mollis a orci. Curabitur mi augue, sagittis ut eleifend ut, tincidunt ut dui. Etiam sed neque mauris, sed sagittis augue. Quisque eu tellus mi, non vehicula sem.

Vestibulum aliquam tincidunt sodales. Cras gravida metus sollicitudin odio consectetur quis aliquam ligula volutpat. Sed ac urna lacus, a iaculis tortor. Praesent nunc purus, egestas non auctor id, suscipit vitae sem. Ut congue libero eget est condimentum ac vestibulum sem vestibulum. Quisque vitae placerat lacus. Nam porta hendrerit pretium. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum luctus ipsum quis ante malesuada porttitor. Phasellus sagittis pulvinar ante vel ultricies. Curabitur ut pulvinar elit. Proin odio dui, scelerisque vel blandit quis, commodo nec ligula. Maecenas ut imperdiet neque. Suspendisse ligula nisi, aliquam vitae dignissim ut, consectetur sit amet nibh. Nunc euismod tempor commodo. Morbi eget enim augue. Aliquam tempus, velit a fringilla fermentum, tellus dolor hendrerit mauris, at fermentum nibh nisi vulputate velit. Sed orci eros, porta quis sodales at, malesuada id tortor. Quisque dictum orci a mauris dictum gravida. Morbi nec nisi sollicitudin eros rhoncus tincidunt a in lacus.

Duis hendrerit nibh vel neque rutrum quis rhoncus lorem porta. Phasellus magna ipsum, laoreet vitae malesuada eu, ultricies et neque. Phasellus auctor tincidunt lectus, vitae interdum tellus gravida eu. Donec tempus tellus a metus blandit blandit. Praesent placerat faucibus auctor. Duis non gravida enim. Fusce in sem magna. Vivamus luctus fermentum bibendum. Morbi orci libero, accumsan ac feugiat nec, mattis id dui. Morbi malesuada varius vulputate. Morbi sagittis ultrices tellus vel lobortis. Suspendisse a lorem ac tellus porttitor auctor. Maecenas imperdiet faucibus cursus. Sed vestibulum leo in leo tincidunt tristique. Praesent eu elit augue.

Nunc auctor rutrum ligula ut consectetur. Integer eget lorem elementum diam hendrerit ullamcorper sit amet sodales odio. Phasellus tellus arcu, tempor et consequat eu, malesuada in odio. Aliquam mollis, ipsum et tristique euismod, augue urna porttitor mauris, quis iaculis ipsum risus ac erat. Phasellus urna nisi, pharetra vitae semper sed, pretium non odio. Cras diam justo, mollis a vulputate non, condimentum in ligula. Proin vulputate tincidunt accumsan. Duis urna justo, dapibus vitae bibendum ac, facilisis at purus. Phasellus euismod adipiscing nunc eget pulvinar. Nullam dui leo, malesuada sed lobortis eget, rutrum vel justo. Phasellus ipsum nunc, aliquet eu aliquet eget, blandit id est. Maecenas eu est massa, sit amet tempus nisl. In vel nulla vitae turpis blandit ultricies. Aenean ornare justo at eros auctor nec interdum neque euismod. Aliquam laoreet, neque ac varius rutrum, purus purus consequat leo, nec pretium dui justo a nulla. Morbi suscipit euismod odio quis viverra. Integer commodo orci vehicula nisi varius euismod. Aenean egestas nulla sed ligula tincidunt id posuere dolor malesuada. """,
            "homepage_url": "https://www.google.com",
            "profile-private": 1,
            "profile-rpg_experience": "I dabble",
            "profile-ttg_experience": "A few rounds of Catan",
            "profile-player_status": "searching",
            "profile-one_shots": 1,
            "profile-online_games": 1,
        },
        "invalid_profile_post": {
            "display_name": "Charles",
            "bio": "Born in the USA",
            "homepage_url": "https://www.google.com",
            "profile-private": 1,
            "profile-rpg_experience": "I dabble",
            "profile-ttg_experience": "A few rounds of Catan",
            "profile-player_status": "ooga shakka",
            "profile-one_shots": 1,
            "profile-online_games": 1,
        },
    }
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse("gamer_profiles:profile-edit")
    with django_assert_max_num_queries(80):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        orig_status = gamer.player_status
        orig_bio = gamer.user.bio
        assert response.status_code == 200
        response = client.post(url, data=post_data_dict[post_data_key])
        assert response.status_code == expected_post_response
        gamer.refresh_from_db()
        if expected_post_response == 302:
            assert gamer.player_status == "searching"
            assert gamer.user.display_name == "Charles"
        else:
            assert gamer.user.bio == orig_bio
            assert gamer.player_status == orig_status


@pytest.mark.parametrize(
    "gamer_to_use, gamer_to_friend, expected_get_response, expected_post_response, should_friend, new_requests",
    [
        (None, "gamer1", 302, None, False, 0),
        ("gamer3", "gamer1", 302, 302, True, 0),
        ("blocked_gamer", "gamer1", 403, 403, False, 0),
        ("gamer1", "prospective_friend", 200, 302, True, 0),
        ("prospective_friend", "gamer1", 200, 302, False, 1),
        ("gamer2", "gamer1", 200, 302, False, 1),
    ],
)
def test_gamer_friend_request(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    gamer_to_friend,
    expected_get_response,
    expected_post_response,
    should_friend,
    new_requests,
):
    gamer_friend = getattr(social_testdata, gamer_to_friend)
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse(
        "gamer_profiles:gamer-friend", kwargs={"gamer": gamer_friend.username}
    )
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url)
        assert response.status_code == expected_post_response
        gamer.refresh_from_db()
        assert (
            models.GamerFriendRequest.objects.filter(
                requestor=gamer, recipient=gamer_friend
            ).count()
            == new_requests
        )
        if should_friend:
            assert gamer_friend in gamer.friends.all()
        else:
            assert gamer_friend not in gamer.friends.all()


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [(None, 302, None), ("gamer2", 405, 403), ("prospective_friend", 405, 302)],
)
def test_friend_request_withdraw(
    client,
    social_testdata,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:gamer-friend-request-delete",
        kwargs={"friend_request": social_testdata.fr.pk},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.GamerFriendRequest.objects.get(pk=social_testdata.fr.pk)
        else:
            assert models.GamerFriendRequest.objects.get(pk=social_testdata.fr.pk)


@pytest.mark.parametrize(
    "view_name, gamer_to_use, expected_get_response, expected_post_response",
    [
        ("approve", None, 302, None),
        ("reject", None, 302, None),
        ("approve", "gamer2", 405, 403),
        ("reject", "gamer2", 405, 403),
        ("approve", "gamer1", 405, 302),
        ("reject", "gamer1", 405, 302),
    ],
)
def test_friend_request_approve_deny(
    client,
    social_testdata,
    assert_login_redirect,
    view_name,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse(
        "gamer_profiles:gamer-friend-request-{}".format(view_name),
        kwargs={"friend_request": social_testdata.fr.pk},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.GamerFriendRequest.objects.get(pk=social_testdata.fr.pk).status
                != "new"
            )
            if "approve" in view_name:
                assert social_testdata.prospective_friend in gamer.friends.all()
            else:
                assert social_testdata.prospective_friend not in gamer.friends.all()
        else:
            assert (
                models.GamerFriendRequest.objects.get(pk=social_testdata.fr.pk).status
                == "new"
            )


@pytest.mark.parametrize("gamer_to_use", [(None), ("gamer1")])
def test_friend_request_list(
    client, social_testdata, assert_login_redirect, gamer_to_use
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
        models.GamerFriendRequest.objects.create(
            requestor=gamer, recipient=social_testdata.gamer5, status="new"
        )
    response = client.get(reverse("gamer_profiles:my-gamer-friend-requests"))
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 200
        assert response.context["pending_requests"].count() == 1
        assert response.context["sent_requests"].count() == 1
        response.context["pending_requests"][0].accept()
        response = client.get(reverse("gamer_profiles:my-gamer-friend-requests"))
        assert response.context["pending_requests"].count() == 0


@pytest.mark.parametrize(
    "view_name, gamer_to_use",
    [
        ("mute-gamer", None),
        ("block-gamer", None),
        ("mute-gamer", "gamer1"),
        ("block-gamer", "gamer1"),
    ],
)
def test_mute_block_gamer(
    client, social_testdata, assert_login_redirect, view_name, gamer_to_use
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse(
        "gamer_profiles:{}".format(view_name),
        kwargs={
            "gamer": social_testdata.gamer3.username,
            "next": reverse("gamer_profiles:my-community-list"),
        },
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 405
        response = client.post(url, data={})
        assert response.status_code == 302
        assert "communities" in response["Location"]
        if "mute" in view_name:
            assert models.MutedUser.objects.get(
                muter=gamer, mutee=social_testdata.gamer3
            )
        else:
            assert models.BlockedUser.objects.get(
                blocker=gamer, blockee=social_testdata.gamer3
            )


@pytest.mark.parametrize(
    "view_name, gamer_to_use, expected_get_response, expected_post_response",
    [
        ("unmute-gamer", None, 302, None),
        ("unblock-gamer", None, 302, None),
        ("unmute-gamer", "gamer2", 405, 403),
        ("unblock-gamer", "gamer2", 405, 403),
        ("unmute-gamer", "gamer1", 405, 302),
        ("unblock-gamer", "gamer1", 405, 302),
    ],
)
def test_remove_mute_block(
    client,
    social_testdata,
    assert_login_redirect,
    view_name,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    if "mute" in view_name:
        record_to_remove = social_testdata.mute_record
        urlkwarg = "mute"
    else:
        record_to_remove = social_testdata.block_record
        urlkwarg = "block"
    url = reverse(
        "gamer_profiles:{}".format(view_name),
        kwargs={
            urlkwarg: record_to_remove.pk,
            "next": reverse("gamer_profiles:my-community-list"),
        },
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert "communities" in response["Location"]
            with pytest.raises(ObjectDoesNotExist):
                type(record_to_remove).objects.get(pk=record_to_remove.pk)
        else:
            assert type(record_to_remove).objects.get(pk=record_to_remove.pk)


@pytest.mark.parametrize("gamer_to_use", [(None), ("gamer1")])
def test_create_gamer_note(
    client, social_testdata, assert_login_redirect, gamer_to_use
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse(
        "gamer_profiles:add-gamer-note",
        kwargs={"gamer": social_testdata.gamer3.username},
    )
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 200
        prev_count = models.GamerNote.objects.filter(
            gamer=social_testdata.gamer3
        ).count()
        response = client.post(
            url, data={"title": "Test note", "body": "Hi **there**!"}
        )
        assert response.status_code == 302
        assert (
            models.GamerNote.objects.filter(gamer=social_testdata.gamer3).count()
            - prev_count
            == 1
        )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, post_data, expected_post_response",
    [
        (None, 302, None, None),
        (
            "gamer3",
            403,
            {"title": "Test note", "body": "I at a whole chicken once."},
            403,
        ),
        ("gamer1", 200, {"monkeys": "Are furry"}, 200),
        (
            "gamer1",
            200,
            {"title": "Test note", "body": "I at a whole chicken once."},
            302,
        ),
    ],
)
def test_update_gamer_note(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    post_data,
    expected_post_response,
):
    if gamer_to_use:
        gamer = getattr(social_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse(
        "gamer_profiles:edit-gamernote", kwargs={"gamernote": social_testdata.gn.pk}
    )
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.GamerNote.objects.get(pk=social_testdata.gn.pk).body
                == post_data["body"]
            )
        else:
            assert (
                models.GamerNote.objects.get(pk=social_testdata.gn.pk).body
                == "This is someone new."
            )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [(None, 302, None), ("gamer2", 403, 403), ("gamer1", 200, 302)],
)
def test_delete_gamer_note(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:delete-gamernote", kwargs={"gamernote": social_testdata.gn.pk}
    )
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.GamerNote.objects.get(pk=social_testdata.gn.pk)
        else:
            assert models.GamerNote.objects.get(pk=social_testdata.gn.pk)


@pytest.mark.parametrize(
    "gamer_to_use, invite_level, expected_get_response",
    [
        (None, "member", 302),
        ("muted_gamer", "member", 403),
        ("gamer3", "member", 200),
        ("gamer3", "admin", 403),
        ("gamer1", "member", 200),
        ("gamer1", "admin", 200),
    ],
)
def test_community_invite_view(
    client,
    social_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    invite_level,
    expected_get_response,
):
    for x in range(3):
        Invite.objects.create(
            creator=social_testdata.gamer1.user,
            label="test {}".format(x),
            content_object=social_testdata.community1,
        )
    social_testdata.community1.add_member(social_testdata.gamer3)
    social_testdata.community1.invites_allowed = "member"
    social_testdata.community1.save()
    Invite.objects.create(
        creator=social_testdata.gamer3.user,
        label="Test invite",
        content_object=social_testdata.community1,
    )
    social_testdata.community1.invites_allowed = invite_level
    social_testdata.community1.save()
    if gamer_to_use:
        client.force_login(user=getattr(social_testdata, gamer_to_use).user)
    url = reverse(
        "gamer_profiles:community_invite_list",
        kwargs={"slug": social_testdata.community1.slug},
    )
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
