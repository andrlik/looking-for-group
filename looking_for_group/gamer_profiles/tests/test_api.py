import pytest
from django.urls import reverse

from .. import models
from ..models import NotInCommunity

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
    url = reverse(viewname, kwargs={"parent_lookup_community": community.pk})
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
        ("gamer1", "api-comm-application-detail", "community", "application", 403),
        (
            "blocked_gamer",
            "api-comm-application-detail",
            "community1",
            "application",
            403,
        ),
        ("new_gamer", "api-comm-application-detail", "community1", "application", 403),
        ("gamer5", "api-comm-application-detail", "community1", "application", 403),
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
        kwargs={"parent_lookup_community": community.pk, "pk": target_object.pk},
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
    url = reverse(viewname, kwargs={"format": "json", "pk": obj.pk})
    with django_assert_max_num_queries(70):
        response = apiclient.get(url)
    assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamertouse,targetgamer,friendviewname,friendaction,expected_get_response,expected_post_response",
    [
        (None, "gamer2", "api-profile-friend", None, 403, 403),
        (None, "gamer2", "api-profile-unfriend", None, 403, 403),
        ("gamer1", "gamer2", "api-profile-friend", "accept", 200, 201),
        ("gamer1", "gamer2", "api-profile-friend", "reject", 200, 201),
        ("gamer1", "gamer3", "api-profile-unfriend", None, 200, 200),
        ("blocked_gamer", "gamer1", "api-profile-unfriend", None, 200, 403),
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
    friending_url = reverse(friendviewname, kwargs={"pk": target_friend.pk})
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
                assert response.status_code == 202
                gamer.refresh_from_db()
                assert gamer.friends.count() - friend_count == 1
            else:
                action_url = reverse(
                    "api-my-received-request-ignore", kwargs={"pk": fr_request.pk}
                )
                response = apiclient.post(action_url)
                assert response.status_code == 202
                fr_request.refresh_from_db()
                assert fr_request.status == "reject"
    elif expected_post_response == 200:
        gamer.refresh_from_db()
        assert friend_count - gamer.friends.count() == 1


@pytest.mark.parametrize(
    "gamertouse,viewname,expected_post_response",
    [
        (None, "api-comm-application-approve", 403),
        ("gamer5", "api-comm-application-approve", 403),
        ("gamer1", "api-comm-application-approve", 202),
        (None, "api-comm-application-reject", 403),
        ("gamer5", "api-comm-application-reject", 403),
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
            "parent_lookup_community": application.community.pk,
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


def test_kick_ban_community_member(
    apiclient,
    django_assert_max_num_queries,
    social_testdata_with_kicks,
    gamertouse,
    viewname,
    targetgamer,
    expected_post_response,
):
    pass
