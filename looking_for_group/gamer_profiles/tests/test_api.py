import logging
from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone

from .. import models, serializers
from ..models import NotInCommunity

logger = logging.getLogger("api")

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "gamertouse,viewname,expected_get_response",
    [
        (None, "api-community-list", 403),
        ("gamer1", "api-community-list", 200),
        (None, "api-profile-list", 403),
        ("gamer1", "api-profile-list", 200),
        (None, "api-my-application-list", 403),
        ("gamer1", "api-my-application-list", 200),
        (None, "api-my-sent-request-list", 403),
        ("gamer1", "api-my-sent-request-list", 200),
        (None, "api-my-received-request-list", 403),
        ("gamer1", "api-my-received-request-list", 200),
        (None, "api-block-list", 403),
        ("gamer1", "api-block-list", 200),
        (None, "api-mute-list", 403),
        ("gamer1", "api-mute-list", 200),
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
    "gamertouse,viewname,httpmethod,targetobject,post_data,expected_post_response",
    [
        (
            None,
            "api-community-list",
            "post",
            None,
            {
                "id": "",
                "slug": "",
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            403,
        ),
        (
            "gamer1",
            "api-community-list",
            "post",
            None,
            {
                "id": "",
                "slug": "",
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            201,
        ),
        (
            None,
            "api-community-detail",
            "put",
            "community",
            {
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            403,
        ),
        (
            "gamer2",
            "api-community-detail",
            "put",
            "community",
            {
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            403,
        ),
        (
            "gamer5",
            "api-community-detail",
            "put",
            "community",
            {
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            200,
        ),
        (
            None,
            "api-community-detail",
            "patch",
            "community",
            {
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            403,
        ),
        (
            "gamer5",
            "api-community-detail",
            "patch",
            "community",
            {
                "name": "My New Community",
                "description": "Itsa me, Community!",
                "url": "https://www.google.com",
            },
            200,
        ),
        (None, "api-community-detail", "delete", "community", {}, 403),
        ("gamer2", "api-community-detail", "delete", "community", {}, 403),
        ("gamer5", "api-community-detail", "delete", "community", {}, 204),
    ],
)
def test_community_destructive_edits(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    viewname,
    httpmethod,
    post_data,
    targetobject,
    expected_post_response,
):
    gamer = None
    target_object = None
    community_count = models.GamerCommunity.objects.count()
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    if targetobject:
        target_object = getattr(social_testdata_with_kicks, targetobject)
        if httpmethod in ["put"]:
            post_data["id"] = target_object.pk
            post_data["slug"] = target_object.slug
        url = reverse(viewname, kwargs={"slug": target_object.slug})
    else:
        url = reverse(viewname)
    with django_assert_max_num_queries(50):
        if httpmethod not in ["get", "delete"]:
            response = getattr(apiclient, httpmethod)(
                url, format="multipart", data=post_data
            )
        else:
            response = getattr(apiclient, httpmethod)(url, data=post_data)
    print(response.data)
    assert response.status_code == expected_post_response
    if expected_post_response == 201:
        assert models.GamerCommunity.objects.count() - community_count == 1
    elif expected_post_response == 204:
        with pytest.raises(ObjectDoesNotExist):
            models.GamerCommunity.objects.get(pk=target_object.pk)
    elif expected_post_response == 200:
        target_object.refresh_from_db()
        for k, v in post_data.items():
            assert v == getattr(target_object, k) or (
                v == "" and not getattr(target_object, k)
            )
    else:
        assert models.GamerCommunity.objects.count() == community_count
        if target_object:
            for k, v in post_data.items():
                if k not in ["id", "slug"]:
                    assert v != getattr(target_object, k)


@pytest.mark.parametrize(
    "gamertouse,viewname,filterstr,communitytouse,expected_get_response",
    [
        (None, "api-member-list", None, "community1", 403),
        ("gamer1", "api-member-list", None, "community1", 200),
        ("gamer5", "api-member-list", None, "community1", 403),
        (None, "api-member-list", "community_role=admin", "community1", 403),
        ("gamer1", "api-member-list", "community_role=admin", "community1", 200),
        ("gamer5", "api-member-list", "community_role=admin", "community1", 403),
        (None, "api-member-list", "community_role=moderator", "community1", 403),
        ("gamer1", "api-member-list", "community_role=moderator", "community1", 200),
        ("gamer5", "api-member-list", "community_role=moderator", "community1", 403),
        (None, "api-comm-ban-list", None, "community1", 403),
        ("gamer1", "api-comm-ban-list", None, "community1", 200),
        ("gamer5", "api-comm-ban-list", None, "community1", 403),
        (None, "api-comm-kick-list", None, "community1", 403),
        ("gamer1", "api-comm-kick-list", None, "community1", 200),
        ("gamer5", "api-comm-kick-list", None, "community1", 403),
        (None, "api-comm-application-list", None, "community1", 403),
        ("gamer1", "api-comm-application-list", None, "community1", 200),
        ("gamer5", "api-comm-application-list", None, "community1", 403),
    ],
)
def test_community_sublists(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    viewname,
    filterstr,
    communitytouse,
    expected_get_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata_with_kicks, communitytouse)
    url = reverse(viewname, kwargs={"parent_lookup_community": community.slug})
    if filterstr:
        url = str(url) + "?{}".format(filterstr)
    with django_assert_max_num_queries(50):
        response = apiclient.get(url)
    assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamertouse,viewname,communitytouse,targetobject,expected_get_response",
    [
        (None, "api-member-detail", "community1", "gamer1", 403),
        (None, "api-comm-ban-detail", "community", "banned1", 403),
        (None, "api-comm-kick-detail", "community1", "kick1", 403),
        (None, "api-comm-application-detail", "community1", "application", 403),
        ("gamer5", "api-member-detail", "community", "gamer1", 200),
        ("gamer1", "api-member-detail", "community", "gamer5", 200),
        ("gamer1", "api-comm-ban-detail", "community", "banned1", 403),
        ("gamer5", "api-comm-ban-detail", "community", "banned1", 200),
        ("gamer5", "api-comm-kick-detail", "community1", "kick1", 403),
        ("blocked_gamer", "api-comm-kick-detail", "community1", "kick1", 403),
        ("gamer1", "api-comm-kick-detail", "community1", "kick1", 200),
        ("gamer1", "api-comm-application-detail", "community1", "application", 200),
        ("gamer1", "api-comm-application-detail", "community", "application", 404),
        (
            "blocked_gamer",
            "api-comm-application-detail",
            "community1",
            "application",
            404,
        ),
        ("new_gamer", "api-comm-application-detail", "community1", "application", 404),
        ("gamer5", "api-comm-application-detail", "community1", "application", 404),
    ],
)
def test_community_sublist_details(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    viewname,
    communitytouse,
    targetobject,
    expected_get_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        print("Logged in as: {}".format(gamer))
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata_with_kicks, communitytouse)
    print("Using community: {}".format(community))
    if viewname == "api-member-detail":
        target_object = models.CommunityMembership.objects.get(
            community=community, gamer=getattr(social_testdata_with_kicks, targetobject)
        )
    else:
        target_object = getattr(social_testdata_with_kicks, targetobject)
    print("Using target object of {}".format(target_object))
    url = reverse(
        viewname,
        kwargs={"parent_lookup_community": community.slug, "pk": target_object.pk},
    )
    with django_assert_max_num_queries(50):
        response = apiclient.get(url)
    assert expected_get_response == response.status_code


@pytest.mark.parametrize(
    "gamertouse,viewname,object_to_use,expected_get_response",
    [
        (None, "api-community-detail", "community1", 403),
        (None, "api-profile-detail", "gamer1", 403),
        ("gamer1", "api-community-detail", "community1", 200),
        ("gamer5", "api-community-detail", "community1", 200),
        ("gamer1", "api-profile-detail", "gamer1", 200),
        ("gamer1", "api-profile-detail", "gamer3", 200),
        ("blocked_gamer", "api-profile-detail", "gamer1", 403),
        (None, "api-my-application-detail", "application", 403),
        ("gamer1", "api-my-application-detail", "application", 404),
        ("gamer5", "api-my-application-detail", "application", 404),
        ("new_gamer", "api-my-application-detail", "application", 200),
    ],
)
def test_top_detail_views(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    viewname,
    object_to_use,
    expected_get_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    obj = getattr(social_testdata_with_kicks, object_to_use)
    if isinstance(obj, models.GamerProfile):
        for gamecheck in models.GamerProfile.objects.all():
            print("{}: {}".format(gamecheck.username, gamecheck.pk))
    if isinstance(obj, models.GamerCommunity):
        url = reverse(viewname, kwargs={"format": "json", "slug": obj.slug})
    elif isinstance(obj, models.GamerProfile):
        url = reverse(viewname, kwargs={"format": "json", "username": obj.username})
    else:
        url = reverse(viewname, kwargs={"format": "json", "pk": obj.pk})
    with django_assert_max_num_queries(70):
        response = apiclient.get(url)
    assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamertouse,gamertoedit,httpmethod,post_data,expected_post_response",
    [
        (None, "gamer1", "put", {"player_status": "available"}, 403),
        ("gamer2", "gamer1", "put", {"player_status": "available"}, 403),
        ("gamer1", "gamer1", "put", {"player_status": "available"}, 200),
        (None, "gamer1", "patch", {"player_status": "available"}, 403),
        ("gamer2", "gamer1", "patch", {"player_status": "available"}, 403),
        ("gamer1", "gamer1", "patch", {"player_status": "available"}, 200),
    ],
)
def test_gamer_profile_update_views(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    gamertoedit,
    httpmethod,
    post_data,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    gamer_to_edit = getattr(social_testdata, gamertoedit)
    url = reverse("api-profile-detail", kwargs={"username": gamer_to_edit.username})
    if httpmethod == "put":
        # Add all the necessary fields.
        data_to_use = serializers.GamerProfileSerializer(
            gamer_to_edit, context={"request": None}
        ).data
        for k, v in post_data.items():
            data_to_use[k] = v
    else:
        data_to_use = {**post_data}
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, data=data_to_use)
    print(response.data)
    assert response.status_code == expected_post_response
    if expected_post_response == 200:
        gamer_to_edit.refresh_from_db()
        for k, v in post_data.items():
            assert getattr(gamer_to_edit, k) == v or (
                v == "" and not getattr(gamer_to_edit, k)
            )


@pytest.mark.parametrize(
    "gamertouse,targetgamer,friendviewname,friendaction,expected_get_response,expected_post_response",
    [
        (None, "gamer2", "api-profile-friend", None, 403, 403),
        (None, "gamer2", "api-profile-unfriend", None, 403, 403),
        ("gamer1", "gamer2", "api-profile-friend", "accept", 200, 201),
        ("gamer1", "gamer2", "api-profile-friend", "reject", 200, 201),
        ("gamer1", "gamer3", "api-profile-unfriend", None, 200, 200),
        ("blocked_gamer", "gamer1", "api-profile-unfriend", None, 200, 400),
    ],
)
def test_friend_request_create_receipt(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    targetgamer,
    friendviewname,
    friendaction,
    expected_get_response,
    expected_post_response,
):
    friend_count = 0
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        print(gamer)
        apiclient.force_login(gamer.user)
        friend_count = gamer.friends.count()
    target_friend = getattr(social_testdata, targetgamer)
    print("Target: {}".format(target_friend))
    friending_url = reverse(friendviewname, kwargs={"username": target_friend.username})
    with django_assert_max_num_queries(50):
        response = apiclient.post(friending_url)
    assert response.status_code == expected_post_response
    if expected_post_response == 201:
        fr_request = models.GamerFriendRequest.objects.get(
            requestor=gamer, recipient=target_friend
        )
        assert fr_request
        if friendaction:
            url = reverse(
                "api-my-received-request-detail", kwargs={"pk": fr_request.pk}
            )
            apiclient.force_login(target_friend.user)
            response = apiclient.get(url)
            assert response.status_code == 200
            if friendaction == "accept":
                action_url = reverse(
                    "api-my-received-request-accept", kwargs={"pk": fr_request.pk}
                )
                response = apiclient.post(action_url)
                assert response.status_code == 200
                gamer.refresh_from_db()
                assert gamer.friends.count() - friend_count == 1
            else:
                action_url = reverse(
                    "api-my-received-request-ignore", kwargs={"pk": fr_request.pk}
                )
                response = apiclient.post(action_url)
                assert response.status_code == 200
                fr_request.refresh_from_db()
                assert fr_request.status == "reject"
    elif expected_post_response == 200:
        gamer.refresh_from_db()
        assert friend_count - gamer.friends.count() == 1


@pytest.mark.parametrize(
    "gamertouse,viewname,expected_post_response",
    [
        (None, "api-comm-application-approve", 403),
        ("gamer5", "api-comm-application-approve", 404),
        ("gamer1", "api-comm-application-approve", 202),
        (None, "api-comm-application-reject", 403),
        ("gamer5", "api-comm-application-reject", 404),
        ("gamer1", "api-comm-application-reject", 202),
    ],
)
def test_community_application_approval(
    apiclient,
    social_testdata_with_kicks,
    django_assert_max_num_queries,
    gamertouse,
    viewname,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    application = social_testdata_with_kicks.application
    url = reverse(
        viewname,
        kwargs={
            "parent_lookup_community": application.community.slug,
            "pk": application.pk,
        },
    )
    with django_assert_max_num_queries(50):
        response = apiclient.post(url)
    assert response.status_code == expected_post_response
    if expected_post_response == 202:
        application.refresh_from_db()
        if "approve" in viewname:
            assert application.status == "approve"
            assert application.community.get_role(application.gamer)
        else:
            assert application.status == "reject"
            with pytest.raises(NotInCommunity):
                application.community.get_role(application.gamer)


@pytest.mark.parametrize(
    "gamertouse,communitytouse,viewname,post_data,targetgamer,expected_post_response",
    [
        (None, "community", "api-member-kick", {"reason": "Obnoxious"}, "gamer1", 403),
        (None, "community", "api-member-ban", {"reason": "Obnoxious"}, "gamer1", 403),
        (
            "gamer1",
            "community",
            "api-member-kick",
            {"reason": "Obnoxious"},
            "gamer5",
            403,
        ),
        (
            "gamer1",
            "community",
            "api-member-ban",
            {"reason": "Obnoxious"},
            "gamer5",
            403,
        ),
        (
            "gamer5",
            "community",
            "api-member-kick",
            {"reason": "Obnoxious"},
            "gamer1",
            201,
        ),
        (
            "gamer5",
            "community",
            "api-member-ban",
            {"reason": "Obnoxious"},
            "gamer1",
            201,
        ),
        ("gamer5", "community", "api-member-kick", {}, "gamer1", 400),
        ("gamer5", "community", "api-member-ban", {}, "gamer1", 400),
    ],
)
def test_kick_ban_community_member(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    communitytouse,
    viewname,
    post_data,
    targetgamer,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata_with_kicks, communitytouse)
    target_gamer = models.CommunityMembership.objects.get(
        gamer=getattr(social_testdata_with_kicks, targetgamer), community=community
    )
    url = reverse(
        viewname,
        kwargs={"parent_lookup_community": community.slug, "pk": target_gamer.pk},
    )
    with django_assert_max_num_queries(50):
        response = apiclient.post(url, data=post_data)
    assert response.status_code == expected_post_response
    if expected_post_response == 201:
        with pytest.raises(ObjectDoesNotExist):
            models.CommunityMembership.objects.get(
                gamer=getattr(social_testdata_with_kicks, targetgamer),
                community=community,
            )
        if "kick" in viewname:
            assert (
                models.KickedUser.objects.filter(
                    community=community, kicked_user=target_gamer.gamer
                ).count()
                > 0
            )
        else:
            assert (
                models.BannedUser.objects.filter(
                    community=community, banned_user=target_gamer.gamer
                ).count()
                > 0
            )
    else:
        assert models.CommunityMembership.objects.get(
            gamer=getattr(social_testdata_with_kicks, targetgamer), community=community
        )
        if "kick" in viewname:
            assert (
                models.KickedUser.objects.filter(
                    community=community, kicked_user=target_gamer.gamer
                ).count()
                == 0
            )
        else:
            assert (
                models.BannedUser.objects.filter(
                    community=community, banned_user=target_gamer.gamer
                ).count()
                == 0
            )


@pytest.mark.parametrize(
    "gamertouse,httpmethod,communitytouse,targetmember,post_data,expected_post_response",
    [
        (None, "put", "community", "gamer1", {"community_role": "admin"}, 403),
        ("gamer1", "put", "community", "gamer1", {"community_role": "admin"}, 403),
        ("gamer5", "put", "community", "gamer1", {"community_role": "admin"}, 200),
        (None, "patch", "community", "gamer1", {"community_role": "admin"}, 403),
        ("gamer1", "patch", "community", "gamer1", {"community_role": "admin"}, 403),
        ("gamer5", "patch", "community", "gamer1", {"community_role": "admin"}, 200),
        ("gamer5", "put", "community", "gamer5", {"community_role": "moderator"}, 403),
    ],
)
def test_edit_community_role(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    httpmethod,
    communitytouse,
    targetmember,
    post_data,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata, communitytouse)
    target_member = community.members.get(gamer=getattr(social_testdata, targetmember))
    url = reverse(
        "api-member-detail",
        kwargs={
            "parent_lookup_community": target_member.community.slug,
            "pk": target_member.pk,
        },
    )
    data_to_use = {**post_data}
    data_to_use["gamer"] = serializers.GamerProfileListSerializer(
        target_member.gamer
    ).data
    if httpmethod == "put":
        data_to_use["id"] = target_member.pk
        data_to_use["community"] = target_member.community.slug
        # data_to_use["median_comm_rating"] = target_member.median_comm_rating
        # data_to_use["comm_reputation_score"] = target_member.comm_reputation_score
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, data=data_to_use)
    print(response.data)
    assert response.status_code == expected_post_response
    target_member.refresh_from_db()
    for k, v in post_data.items():
        if expected_post_response == 200:
            assert getattr(target_member, k) == v
        else:
            assert getattr(target_member, k) != v


@pytest.mark.parametrize(
    "gamertouse,communitytouse,viewname,expected_post_response",
    [
        (None, "community_public", "api-community-join", 403),
        (None, "community_public", "api-community-leave", 403),
        ("gamer4", "community_public", "api-community-join", 201),
        ("gamer4", "community_public", "api-community-leave", 403),
        ("gamer1", "community_public", "api-community-leave", 204),
        ("gamer3", "community_public", "api-community-leave", 400),
    ],
)
def test_join_leave_community(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    communitytouse,
    viewname,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata, communitytouse)
    url = reverse(viewname, kwargs={"slug": community.slug})
    with django_assert_max_num_queries(50):
        response = apiclient.post(url, data={})
    print(response.data)
    assert response.status_code == expected_post_response
    if expected_post_response == 201:
        assert models.CommunityMembership.objects.get(community=community, gamer=gamer)
    elif expected_post_response == 204:
        with pytest.raises(ObjectDoesNotExist):
            models.CommunityMembership.objects.get(community=community, gamer=gamer)


@pytest.mark.parametrize(
    "gamertouse,communitytouse,targetgamer,expected_post_response",
    [
        (None, "community2", "gamer2", 403),
        ("gamer2", "community2", "gamer2", 403),
        ("gamer5", "community2", "gamer3", 400),
        ("gamer5", "community2", "gamer1", 400),
        ("gamer5", "community2", "gamer2", 200),
    ],
)
def test_transfer_ownership(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    communitytouse,
    targetgamer,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata_with_kicks, communitytouse)
    previous_owner = community.owner
    target_gamer = getattr(social_testdata_with_kicks, targetgamer)
    url = reverse("api-community-transfer", kwargs={"slug": community.slug})
    with django_assert_max_num_queries(50):
        response = apiclient.post(url, data={"username": target_gamer.username})
    print(response.data)
    assert response.status_code == expected_post_response
    community.refresh_from_db()
    if expected_post_response == 200:
        assert community.owner == target_gamer
    else:
        assert community.owner == previous_owner


@pytest.mark.parametrize(
    "gamertouse,communitytouse,viewname,httpmethod,targetobject,post_data,expected_post_response",
    [
        (None, "community2", "api-comm-kick-detail", "delete", "kick1", {}, 403),
        (
            None,
            "community2",
            "api-comm-kick-detail",
            "put",
            "kick1",
            {"reason": "He's super annoying."},
            403,
        ),
        (
            None,
            "community2",
            "api-comm-kick-detail",
            "patch",
            "kick1",
            {"reason": "He's super annoying."},
            403,
        ),
        (None, "community", "api-comm-ban-detail", "delete", "banned1", {}, 403),
        (
            None,
            "community",
            "api-comm-ban-detail",
            "put",
            "banned1",
            {"reason": "harrassment extreme"},
            403,
        ),
        (
            None,
            "community",
            "api-comm-ban-detail",
            "patch",
            "banned1",
            {"reason": "harrassment extreme"},
            403,
        ),
        ("gamer4", "community2", "api-comm-kick-detail", "delete", "kick1", {}, 404),
        (
            "gamer4",
            "community2",
            "api-comm-kick-detail",
            "put",
            "kick1",
            {"reason": "He's super annoying."},
            404,
        ),
        (
            "gamer4",
            "community2",
            "api-comm-kick-detail",
            "patch",
            "kick1",
            {"reason": "He's super annoying."},
            404,
        ),
        ("gamer4", "community", "api-comm-ban-detail", "delete", "banned1", {}, 403),
        (
            "gamer4",
            "community",
            "api-comm-ban-detail",
            "put",
            "banned1",
            {"reason": "harrassment extreme"},
            405,
        ),
        (
            "gamer4",
            "community",
            "api-comm-ban-detail",
            "patch",
            "banned1",
            {"reason": "harrassment extreme"},
            405,
        ),
        ("gamer1", "community1", "api-comm-kick-detail", "delete", "kick1", {}, 204),
        (
            "gamer1",
            "community1",
            "api-comm-kick-detail",
            "put",
            "kick1",
            {"reason": "He's super annoying."},
            200,
        ),
        (
            "gamer1",
            "community1",
            "api-comm-kick-detail",
            "patch",
            "kick1",
            {"reason": "He's super annoying."},
            200,
        ),
        ("gamer1", "community", "api-comm-ban-detail", "delete", "banned1", {}, 403),
        (
            "gamer1",
            "community",
            "api-comm-ban-detail",
            "put",
            "banned1",
            {"reason": "harrassment extreme"},
            405,
        ),
        (
            "gamer1",
            "community",
            "api-comm-ban-detail",
            "patch",
            "banned1",
            {"reason": "harrassment extreme"},
            405,
        ),
        ("gamer5", "community", "api-comm-ban-detail", "delete", "banned1", {}, 204),
        (
            "gamer5",
            "community",
            "api-comm-ban-detail",
            "put",
            "banned1",
            {"reason": "harrassment extreme"},
            405,
        ),
        (
            "gamer5",
            "community",
            "api-comm-ban-detail",
            "patch",
            "banned1",
            {"reason": "harrassment extreme"},
            405,
        ),
    ],
)
def test_kick_ban_edits(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    communitytouse,
    viewname,
    httpmethod,
    targetobject,
    post_data,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    community = getattr(social_testdata_with_kicks, communitytouse)
    target_object = getattr(social_testdata_with_kicks, targetobject)
    logger.debug(
        "Preparing to submit {} method with data of {}".format(httpmethod, post_data)
    )
    url = reverse(
        viewname,
        kwargs={"parent_lookup_community": community.slug, "pk": target_object.pk},
    )
    if httpmethod in ["patch", "delete"]:
        data_to_submit = post_data
    else:
        if "ban" in viewname:
            data_to_submit = {
                # "id": target_object.pk,
                # "community": community.name,
                # "banner": target_object.banner.username,
                # "banned_user": target_object.banned_user.username,
                "reason": post_data["reason"]
            }
        else:
            data_to_submit = {
                "id": target_object.pk,
                "community": community.slug,
                "kicker": target_object.kicker.username,
                "kicked_user": target_object.kicked_user.username,
                "reason": post_data["reason"],
                "end_date": (timezone.now() + timedelta(days=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
            }
        logger.debug("Translated post data to {}".format(data_to_submit))
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, data=data_to_submit)
    print(response.data)
    assert response.status_code == expected_post_response
    if expected_post_response == 200:
        target_object.refresh_from_db()
        if post_data:
            for k, v in post_data.items():
                assert v == getattr(target_object, k) or (
                    v == "" and not getattr(target_object, k)
                )
    if expected_post_response == 204:
        with pytest.raises(ObjectDoesNotExist):
            type(target_object).objects.get(pk=target_object.pk)


@pytest.mark.parametrize(
    "gamertouse,viewname,targetgamer,notetouse,expected_get_response,expected_length",
    [
        (None, "api-gamernote-list", "gamer3", None, 403, None),
        (None, "api-gamernote-detail", "gamer3", "gn", 403, None),
        ("gamer2", "api-gamernote-list", "gamer3", None, 200, 0),
        ("gamer2", "api-gamernote-detail", "gamer3", "gn", 404, None),
        ("gamer4", "api-gamernote-list", "gamer3", None, 200, 0),
        ("gamer4", "api-gamernote-detail", "gamer3", "gn", 404, None),
        ("gamer1", "api-gamernote-list", "gamer3", None, 200, 1),
        ("gamer1", "api-gamernote-detail", "gamer3", "gn", 200, None),
    ],
)
def test_gamernote_list_detail(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    viewname,
    targetgamer,
    notetouse,
    expected_get_response,
    expected_length,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    target_gamer = getattr(social_testdata_with_kicks, targetgamer)
    url_kwargs = {"parent_lookup_gamer": target_gamer.username}
    if notetouse:
        url_kwargs["pk"] = getattr(social_testdata_with_kicks, notetouse).pk
    url = reverse(viewname, kwargs=url_kwargs)
    with django_assert_max_num_queries(50):
        response = apiclient.get(url)
    print(response.data)
    assert response.status_code == expected_get_response
    if expected_length:
        assert len(response.data["results"]) == expected_length


@pytest.mark.parametrize(
    "gamertouse,targetgamer,viewname,httpmethod,targetobject,post_data,expected_post_response",
    [
        (
            None,
            "gamer3",
            "api-gamernote-list",
            "post",
            None,
            {"body": "This guy's wise", "title": "I like him"},
            403,
        ),
        (
            "gamer2",
            "gamer3",
            "api-gamernote-list",
            "post",
            None,
            {"body": "This guy's wise", "title": "I like him"},
            201,
        ),
        (
            "gamer1",
            "gamer3",
            "api-gamernote-list",
            "post",
            None,
            {"body": "This guy's wise", "title": "I like him"},
            201,
        ),
        (
            None,
            "gamer3",
            "api-gamernote-detail",
            "put",
            "gn",
            {"body": "This guy's wise", "title": "I like him"},
            403,
        ),
        (
            "gamer2",
            "gamer3",
            "api-gamernote-detail",
            "put",
            "gn",
            {"body": "This guy's wise", "title": "I like him"},
            404,
        ),
        (
            "gamer1",
            "gamer3",
            "api-gamernote-detail",
            "put",
            "gn",
            {"body": "This guy's wise", "title": "I like him"},
            200,
        ),
        (
            None,
            "gamer3",
            "api-gamernote-detail",
            "patch",
            "gn",
            {"body": "This guy's wise", "title": "I like him"},
            403,
        ),
        (
            "gamer2",
            "gamer3",
            "api-gamernote-detail",
            "patch",
            "gn",
            {"body": "This guy's wise", "title": "I like him"},
            404,
        ),
        (
            "gamer1",
            "gamer3",
            "api-gamernote-detail",
            "patch",
            "gn",
            {"body": "This guy's wise", "title": "I like him"},
            200,
        ),
        (None, "gamer3", "api-gamernote-detail", "delete", "gn", {}, 403),
        ("gamer2", "gamer3", "api-gamernote-detail", "delete", "gn", {}, 404),
        ("gamer1", "gamer3", "api-gamernote-detail", "delete", "gn", {}, 204),
    ],
)
def test_gamernote_create_update(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    targetgamer,
    viewname,
    httpmethod,
    targetobject,
    post_data,
    expected_post_response,
):
    gamer = None
    target_object = None
    if gamertouse:
        gamer = getattr(social_testdata_with_kicks, gamertouse)
        apiclient.force_login(gamer.user)
    target_gamer = getattr(social_testdata_with_kicks, targetgamer)
    target_gamer.friends.add(getattr(social_testdata_with_kicks, "gamer1"))
    current_note_count = models.GamerNote.objects.filter(gamer=target_gamer).count()
    if "detail" in viewname or "destroy" in viewname:
        target_object = getattr(social_testdata_with_kicks, targetobject)
        url = reverse(
            viewname,
            kwargs={
                "parent_lookup_gamer": target_gamer.username,
                "pk": target_object.pk,
            },
        )
        if httpmethod == "put":
            post_data["id"] = target_object.pk
            post_data["author"] = target_object.author.username
            post_data["gamer"] = target_object.gamer.username
    else:
        url = reverse(viewname, kwargs={"parent_lookup_gamer": target_gamer.username})
    print(url)
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, post_data)
    print(response.data)
    assert response.status_code == expected_post_response
    if target_object:
        if expected_post_response == 204:
            with pytest.raises(ObjectDoesNotExist):
                models.GamerNote.objects.get(pk=target_object.pk)
        if expected_post_response == 200:
            target_object.refresh_from_db()
            for k, v in post_data.items():
                if hasattr(getattr(target_object, k), "username"):
                    assert v == getattr(target_object, k).username
                else:
                    assert v == getattr(target_object, k)
    else:
        if expected_post_response == 201:
            assert (
                models.GamerNote.objects.filter(gamer=target_gamer).count()
                - current_note_count
                == 1
            )
        else:
            assert (
                models.GamerNote.objects.filter(gamer=target_gamer).count()
                == current_note_count
            )


@pytest.mark.parametrize(
    "gamertouse,targetgamer,viewname,expected_post_response",
    [
        (None, "gamer1", "api-profile-block", 403),
        (None, "gamer1", "api-profile-mute", 403),
        ("gamer1", "muted_gamer", "api-profile-mute", 400),
        ("gamer1", "blocked_gamer", "api-profile-block", 400),
        ("gamer1", "gamer3", "api-profile-mute", 201),
        ("gamer1", "gamer3", "api-profile-block", 201),
        ("gamer1", "gamer1", "api-profile-mute", 400),
        ("gamer1", "gamer1", "api-profile-block", 400),
    ],
)
def test_block_mute_gamer(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    targetgamer,
    viewname,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    target_gamer = getattr(social_testdata, targetgamer)
    total_records = 0
    if "mute" in viewname:
        total_records = models.MutedUser.objects.filter(mutee=target_gamer).count()
    else:
        total_records = models.BlockedUser.objects.filter(blockee=target_gamer).count()
    url = reverse(viewname, kwargs={"username": target_gamer.username})
    with django_assert_max_num_queries(50):
        response = apiclient.post(url)
    print(response.data)
    assert response.status_code == expected_post_response
    if expected_post_response == 201:
        if "mute" in viewname:
            assert (
                models.MutedUser.objects.filter(mutee=target_gamer).count()
                - total_records
                == 1
            )
        else:
            assert (
                models.BlockedUser.objects.filter(blockee=target_gamer).count()
                - total_records
                == 1
            )
    else:
        if "mute" in viewname:
            assert (
                models.MutedUser.objects.filter(mutee=target_gamer).count()
                == total_records
            )
        else:
            assert (
                models.BlockedUser.objects.filter(blockee=target_gamer).count()
                == total_records
            )


@pytest.mark.parametrize(
    "gamertouse,recordtouse,viewname,httpmethod,expected_response",
    [
        (None, "mute_record", "api-mute-detail", "get", 403),
        (None, "block_record", "api-block-detail", "get", 403),
        (None, "mute_record", "api-mute-detail", "delete", 403),
        (None, "block_record", "api-block-detail", "delete", 403),
        ("gamer2", "mute_record", "api-mute-detail", "get", 404),
        ("gamer2", "block_record", "api-block-detail", "get", 404),
        ("gamer2", "mute_record", "api-mute-detail", "delete", 404),
        ("gamer2", "block_record", "api-block-detail", "delete", 404),
        ("gamer1", "mute_record", "api-mute-detail", "get", 200),
        ("gamer1", "block_record", "api-block-detail", "get", 200),
        ("gamer1", "mute_record", "api-mute-detail", "delete", 204),
        ("gamer1", "block_record", "api-block-detail", "delete", 204),
    ],
)
def test_retrieve_destroy_block_mute(
    apiclient,
    django_assert_max_num_queries,
    social_testdata,
    gamertouse,
    recordtouse,
    viewname,
    httpmethod,
    expected_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(social_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    target_object = getattr(social_testdata, recordtouse)
    url = reverse(viewname, kwargs={"pk": target_object.pk})
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url)
    print(response.data)
    assert response.status_code == expected_response
    if httpmethod == "delete":
        if expected_response == 204:
            with pytest.raises(ObjectDoesNotExist):
                type(target_object).objects.get(pk=target_object.pk)
        else:
            assert type(target_object).objects.get(pk=target_object.pk)
