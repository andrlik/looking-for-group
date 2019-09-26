import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.urls import reverse
from factory.django import mute_signals

from .. import models
from ..signals import issue_state_changed
from ..tasks import create_remote_issue, delete_remote_issue, queue_issue_for_sync

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "view_name,get_params,gamertouse,expected_get_response,expected_object_length,expected_location",
    [
        ("helpdesk:issue-list", None, None, 302, None, "/accounts/login/"),
        ("helpdesk:issue-list", None, "gamer1", 200, 5, None),
        ("helpdesk:issue-list", "?status=closed", "gamer1", 200, 0, None),
        ("helpdesk:my-issue-list", None, None, 302, None, "/accounts/login/"),
        ("helpdesk:my-issue-list", None, "gamer1", 200, 2, None),
        ("helpdesk:my-issue-list", "?status=closed", "gamer1", 200, 0, None),
    ],
)
def test_issue_list_view(
    client,
    helpdesk_testdata,
    django_assert_max_num_queries,
    view_name,
    get_params,
    gamertouse,
    expected_get_response,
    expected_object_length,
    expected_location,
):
    gamer = None
    if gamertouse:
        gamer = getattr(helpdesk_testdata, gamertouse)
        client.force_login(user=gamer.user)
    url = reverse(view_name)
    if get_params:
        url = url + get_params
    with django_assert_max_num_queries(50):
        response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_location:
        assert expected_location in response["Location"]
    else:
        assert len(response.context["issue_list"]) == expected_object_length


@pytest.mark.parametrize(
    "issue_to_use,gamertouse,expected_get_response,expected_comment_length,expected_location",
    [
        ("issue1", None, 302, None, "/accounts/login/"),
        ("issue1", "gamer1", 200, 3, None),
        ("issue2", "gamer1", 200, 3, None),
        ("issue4", "gamer1", 200, None, None),
        ("issue4", "gamer2", 403, None, None),
    ],
)
def test_issue_detail_view(
    client,
    helpdesk_testdata,
    django_assert_max_num_queries,
    issue_to_use,
    gamertouse,
    expected_get_response,
    expected_comment_length,
    expected_location,
):
    gamer = None
    if gamertouse:
        gamer = getattr(helpdesk_testdata, gamertouse)
        client.force_login(gamer.user)
    url = getattr(helpdesk_testdata, issue_to_use).get_absolute_url()
    with django_assert_max_num_queries(50):
        response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_response == 302:
        assert expected_location in response["Location"]
    if expected_get_response == 200:
        if expected_comment_length:
            assert (
                len(response.context["reconciled_comments"]) == expected_comment_length
            )


@pytest.mark.parametrize(
    "issue_to_use,gamertouse,expected_get_response,expected_get_location,post_data,expected_post_response",
    [
        ("issue1", None, 302, "/accounts/login/", None, None),
        ("issue1", "gamer2", 403, None, None, 403),
        (
            "issue1",
            "gamer1",
            200,
            None,
            {
                "cached_title": "I'm different!",
                "cached_description": "Feel the fresh wind on your face!",
            },
            302,
        ),
        (
            "issue1",
            "gamer1",
            200,
            None,
            {
                "cached_description": "Moneys are here",
                "cached_title": """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras ipsum nibh, tempus et feugiat sit amet, egestas tincidunt tortor. Fusce pellentesque laoreet ultrices. Proin luctus ullamcorper erat, in rhoncus ipsum semper sit amet. Suspendisse felis risus, placerat a semper sed, commodo eu velit. Sed feugiat venenatis ultricies. Vivamus ullamcorper, leo eget mollis mollis, libero nisl pulvinar nisi, non pharetra nulla odio vitae purus. Pellentesque et libero eros, sed tincidunt ligula. Phasellus id metus justo. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Ut mollis tincidunt bibendum.

Pellentesque faucibus, risus eu mattis viverra, tortor tellus lobortis nibh, vel suscipit justo odio euismod mauris. Etiam consectetur, lorem sit amet iaculis rhoncus, nulla sapien dictum erat, id eleifend ligula neque congue sapien. Proin in posuere risus. Nullam porttitor venenatis velit, id malesuada urna egestas eget. Praesent eget turpis vitae elit suscipit luctus et vel lectus. Etiam sapien nulla, imperdiet porta accumsan in, facilisis et lacus. Etiam risus dui, ornare eget fringilla eget, consequat vel odio. Nam diam leo, lacinia sit amet sagittis vel, blandit nec felis. Pellentesque mattis malesuada orci, ac lobortis lacus pellentesque sit amet. Morbi tempus diam eu quam luctus tempor. Mauris pretium, lectus id elementum faucibus, turpis urna dignissim metus, eu viverra nibh purus id nisi. Nunc id nunc quam. Suspendisse vitae lacus nisl, vel placerat libero. Donec dui enim, congue ac dictum id, ullamcorper sit amet elit. Maecenas nunc purus, viverra id placerat vitae, mollis a orci. Curabitur mi augue, sagittis ut eleifend ut, tincidunt ut dui. Etiam sed neque mauris, sed sagittis augue. Quisque eu tellus mi, non vehicula sem.

Vestibulum aliquam tincidunt sodales. Cras gravida metus sollicitudin odio consectetur quis aliquam ligula volutpat. Sed ac urna lacus, a iaculis tortor. Praesent nunc purus, egestas non auctor id, suscipit vitae sem. Ut congue libero eget est condimentum ac vestibulum sem vestibulum. Quisque vitae placerat lacus. Nam porta hendrerit pretium. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum luctus ipsum quis ante malesuada porttitor. Phasellus sagittis pulvinar ante vel ultricies. Curabitur ut pulvinar elit. Proin odio dui, scelerisque vel blandit quis, commodo nec ligula. Maecenas ut imperdiet neque. Suspendisse ligula nisi, aliquam vitae dignissim ut, consectetur sit amet nibh. Nunc euismod tempor commodo. Morbi eget enim augue. Aliquam tempus, velit a fringilla fermentum, tellus dolor hendrerit mauris, at fermentum nibh nisi vulputate velit. Sed orci eros, porta quis sodales at, malesuada id tortor. Quisque dictum orci a mauris dictum gravida. Morbi nec nisi sollicitudin eros rhoncus tincidunt a in lacus.

Duis hendrerit nibh vel neque rutrum quis rhoncus lorem porta. Phasellus magna ipsum, laoreet vitae malesuada eu, ultricies et neque. Phasellus auctor tincidunt lectus, vitae interdum tellus gravida eu. Donec tempus tellus a metus blandit blandit. Praesent placerat faucibus auctor. Duis non gravida enim. Fusce in sem magna. Vivamus luctus fermentum bibendum. Morbi orci libero, accumsan ac feugiat nec, mattis id dui. Morbi malesuada varius vulputate. Morbi sagittis ultrices tellus vel lobortis. Suspendisse a lorem ac tellus porttitor auctor. Maecenas imperdiet faucibus cursus. Sed vestibulum leo in leo tincidunt tristique. Praesent eu elit augue.

Nunc auctor rutrum ligula ut consectetur. Integer eget lorem elementum diam hendrerit ullamcorper sit amet sodales odio. Phasellus tellus arcu, tempor et consequat eu, malesuada in odio. Aliquam mollis, ipsum et tristique euismod, augue urna porttitor mauris, quis iaculis ipsum risus ac erat. Phasellus urna nisi, pharetra vitae semper sed, pretium non odio. Cras diam justo, mollis a vulputate non, condimentum in ligula. Proin vulputate tincidunt accumsan. Duis urna justo, dapibus vitae bibendum ac, facilisis at purus. Phasellus euismod adipiscing nunc eget pulvinar. Nullam dui leo, malesuada sed lobortis eget, rutrum vel justo. Phasellus ipsum nunc, aliquet eu aliquet eget, blandit id est. Maecenas eu est massa, sit amet tempus nisl. In vel nulla vitae turpis blandit ultricies. Aenean ornare justo at eros auctor nec interdum neque euismod. Aliquam laoreet, neque ac varius rutrum, purus purus consequat leo, nec pretium dui justo a nulla. Morbi suscipit euismod odio quis viverra. Integer commodo orci vehicula nisi varius euismod. Aenean egestas nulla sed ligula tincidunt id posuere dolor malesuada.""",
            },
            200,
        ),
        ("issue4", "gamer2", 404, None, None, 404),
    ],
)
def test_issue_update_view(
    client,
    helpdesk_testdata,
    django_assert_max_num_queries,
    issue_to_use,
    gamertouse,
    expected_get_response,
    expected_get_location,
    post_data,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(helpdesk_testdata, gamertouse)
        client.force_login(gamer.user)
    issue = getattr(helpdesk_testdata, issue_to_use)
    if issue.external_id:
        url = reverse("helpdesk:issue-update", kwargs={"ext_id": issue.external_id})
    else:
        url = reverse("helpdesk:issue-update", kwargs={"ext_id": issue.pk})
    with django_assert_max_num_queries(50):
        response = client.get(url)
    assert expected_get_response == response.status_code
    if expected_get_location:
        assert expected_get_location in response["Location"]
    else:
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            issue.refresh_from_db()
            assert issue.cached_description == post_data["cached_description"]


@pytest.mark.parametrize(
    "gamertouse,expected_get_response,expected_get_location,expected_post_response",
    [
        (None, 302, "/accounts/login/", None),
        ("gamer2", 403, None, 403),
        ("gamer1", 403, None, 403),
        ("super_gamer", 200, None, 302),
    ],
)
def test_delete_issue(
    client,
    helpdesk_testdata,
    gamertouse,
    expected_get_response,
    expected_get_location,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(helpdesk_testdata, gamertouse)
        client.force_login(gamer.user)
    issue = models.IssueLink.objects.create(
        cached_title="Test from delete method",
        cached_description="Yes, let's do that.",
        cached_status="opened",
        creator=getattr(helpdesk_testdata, "gamer1").user,
    )
    create_remote_issue(issue)
    url = reverse("helpdesk:issue-delete", kwargs={"ext_id": issue.external_id})
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    else:
        response = client.post(url, data={})
        assert expected_post_response == response.status_code
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.IssueLink.objects.get(pk=issue.pk)
        else:
            assert models.IssueLink.objects.get(pk=issue.pk)
            delete_remote_issue(issue)
            issue.delete()


@pytest.mark.parametrize(
    "issue_to_use,gamertouse,expected_get_response,expected_get_location,post_data,expected_post_response",
    [
        ("issue2", None, 302, "/accounts/login/", None, None),
        (
            "issue2",
            "gamer1",
            200,
            None,
            {"cached_body": "Hi there. I am a comment."},
            302,
        ),
        (
            "issue2",
            "super_gamer",
            200,
            None,
            {
                "cached_body": "Hi, I'm a commment that will close this issue.",
                "close_issue": 1,
            },
            302,
        ),
    ],
)
def test_add_comment_to_issue(
    client,
    helpdesk_testdata,
    django_assert_max_num_queries,
    issue_to_use,
    gamertouse,
    expected_get_response,
    expected_get_location,
    post_data,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(helpdesk_testdata, gamertouse)
        client.force_login(gamer.user)
    issue = getattr(helpdesk_testdata, issue_to_use)
    url = reverse("helpdesk:issue-add-comment", kwargs={"ext_id": issue.external_id})
    with django_assert_max_num_queries(50):
        response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    else:
        issue.refresh_from_db()
        comment_count = models.IssueCommentLink.objects.filter(
            master_issue=issue
        ).count()
        old_issue_comment_count = issue.cached_comment_count
        assert old_issue_comment_count == comment_count
        with mute_signals(post_save, issue_state_changed):
            response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            # queue_issue_for_sync(issue)
            assert (
                models.IssueCommentLink.objects.filter(master_issue=issue).count()
                - comment_count
                == 1
            )
            issue.refresh_from_db()
            # assert issue.cached_comment_count - old_issue_comment_count == 1
            assert (
                models.IssueCommentLink.objects.filter(master_issue=issue)
                .latest("created")
                .external_id
            )
            assert gamer.user in issue.subscribers.all()
            if "close_issue" in post_data.keys():
                assert issue.cached_status == "closed"
            else:
                assert issue.cached_status == "opened"


@pytest.mark.parametrize(
    "comment_to_use,gamertouse,expected_get_response,expected_get_location,post_data,expected_post_response",
    [
        ("comment1", None, 302, "/accounts/login/", None, None),
        (
            "comment1",
            "gamer1",
            403,
            None,
            {"cached_body": "I am a nefarious user"},
            403,
        ),
        ("comment1", "gamer2", 200, None, {"cached_body": "I am a legit user."}, 302),
        (
            "comment1",
            "super_gamer",
            200,
            None,
            {"cached_body": "I am a super user."},
            302,
        ),
    ],
)
def test_update_comment(
    client,
    django_assert_max_num_queries,
    helpdesk_testdata,
    comment_to_use,
    gamertouse,
    expected_get_response,
    expected_get_location,
    post_data,
    expected_post_response,
):
    gamer = None
    if gamertouse:
        gamer = getattr(helpdesk_testdata, gamertouse)
        client.force_login(gamer.user)
    comment = getattr(helpdesk_testdata, comment_to_use)
    previous_sync = comment.last_sync
    url = reverse(
        "helpdesk:issue-edit-comment",
        kwargs={
            "ext_id": comment.master_issue.external_id,
            "cext_id": comment.external_id,
        },
    )
    with django_assert_max_num_queries(50):
        response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    else:
        response = client.post(url, post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            comment.refresh_from_db()
            assert comment.cached_body == post_data["cached_body"]
            assert comment.sync_status in ["sync", "updating", "update_err"]
            if comment.sync_status == "sync":
                assert comment.last_sync > previous_sync
