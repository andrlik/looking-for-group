import pytest

from .. import models, tasks

pytestmark = pytest.mark.django_db(transaction=True)


def test_create_remote_issue(helpdesk_testdata):
    gl = helpdesk_testdata.gl
    issue = helpdesk_testdata.issue4
    assert not issue.external_id
    tasks.create_remote_issue(issue)
    issue.refresh_from_db()
    assert issue.external_id
    assert issue.external_url
    assert issue.sync_status == "sync"
    remote_issue = issue.get_external_issue(lazy=True, backend_object=gl)
    remote_issue.delete()


@pytest.mark.parametrize(
    "issuename,start_sync_status,expected_end_sync_status",
    [("issue1", "sync", "sync"), ("issue4", "pending", "pending")],
)
def test_update_remote_issue(
    helpdesk_testdata, issuename, start_sync_status, expected_end_sync_status
):
    gl = helpdesk_testdata.gl
    issue = getattr(helpdesk_testdata, issuename)
    issue.sync_status = start_sync_status
    issue.save()
    issue.cached_title = "Monkey town!"
    tasks.update_remote_issue(issue)
    issue.refresh_from_db()
    assert issue.sync_status == expected_end_sync_status
    if expected_end_sync_status == "sync":
        assert issue.cached_title == issue.get_external_issue(backend_object=gl).title


@pytest.mark.parametrize(
    "issuename,start_sync_status,expected_end_sync_status",
    [
        ("issue4", "pending", "pending"),
        ("issue4", "updating", "updating"),
        ("issue4", "sync", "deleted"),
    ],
)
def test_delete_remote_issue(
    helpdesk_testdata, issuename, start_sync_status, expected_end_sync_status
):
    issue = getattr(helpdesk_testdata, issuename)
    if start_sync_status != "pending":
        tasks.create_remote_issue(issue)
        issue.refresh_from_db()
        issue.sync_status = start_sync_status
        issue.save()
    tasks.delete_remote_issue(issue)
    issue.refresh_from_db()
    assert issue.sync_status == expected_end_sync_status
    if expected_end_sync_status == "deleted":
        assert not issue.external_id


@pytest.mark.parametrize(
    "issuename,commenttext,expected_sync_status,expected_state",
    [
        ("issue1", "This is done.", "sync", "closed"),
        ("issue1", None, "sync", "closed"),
        ("issue4", "Hi there", "pending", "opened"),
    ],
)
def test_close_remote_issue(
    helpdesk_testdata, issuename, commenttext, expected_sync_status, expected_state
):
    issue = getattr(helpdesk_testdata, issuename)
    tasks.close_remote_issue(issue, commenttext)
    issue.refresh_from_db()
    assert issue.sync_status == expected_sync_status
    if expected_sync_status == "sync":
        assert (
            "closed"
            == issue.get_external_issue(backend_object=helpdesk_testdata.gl).state
        )
        assert issue.cached_status == "closed"
    if commenttext and expected_sync_status == "sync":
        comments = issue.get_external_comments(backend_object=helpdesk_testdata.gl)
        comment_bodies = [c.body for c in comments]
        assert commenttext in comment_bodies
        comments = issue.comments.all()
        assert commenttext in [c.cached_body for c in comments]


@pytest.mark.parametrize(
    "issuename,expected_sync_status,expected_state",
    [("issue1", "sync", "opened"), ("issue4", "pending", "opened")],
)
def test_reopen_remote_issue(
    helpdesk_testdata, issuename, expected_sync_status, expected_state
):
    issue = getattr(helpdesk_testdata, issuename)
    tasks.close_remote_issue(issue)
    issue.refresh_from_db()
    tasks.reopen_remote_issue(issue)
    issue.refresh_from_db()
    assert issue.sync_status == expected_sync_status
    assert issue.cached_status == expected_state
    if expected_sync_status == "sync":
        assert (
            issue.get_external_issue(backend_object=helpdesk_testdata.gl).state
            == expected_state
        )


def test_create_remote_comment(helpdesk_testdata):
    comment = helpdesk_testdata.comment4
    tasks.create_remote_comment(comment)
    comment.refresh_from_db()
    assert comment.sync_status == "sync"
    assert comment.external_id
    remote_comment = comment.get_external_comment(backend_object=helpdesk_testdata.gl)
    assert remote_comment.id
    remote_comment.delete()


@pytest.mark.parametrize(
    "commentname,expected_sync_status", [("comment1", "sync"), ("comment4", "pending")]
)
def test_update_remote_comment(helpdesk_testdata, commentname, expected_sync_status):
    comment = getattr(helpdesk_testdata, commentname)
    comment.cached_body = "Something new and exciting here."
    comment.save()
    tasks.update_remote_comment(comment)
    comment.refresh_from_db()
    assert comment.sync_status == expected_sync_status
    if expected_sync_status == "sync":
        assert (
            "Something new and exciting here."
            == comment.get_external_comment(backend_object=helpdesk_testdata.gl).body
        )


@pytest.mark.parametrize(
    "commentname,expected_sync_status",
    [("comment1", "deleted"), ("comment4", "pending")],
)
def test_delete_remote_comment(helpdesk_testdata, commentname, expected_sync_status):
    comment = getattr(helpdesk_testdata, commentname)
    tasks.delete_remote_comment(comment)
    comment.refresh_from_db()
    assert comment.sync_status == expected_sync_status


def test_sync_all_issues(helpdesk_testdata):
    gl = helpdesk_testdata.gl
    gl.edit_issue(
        helpdesk_testdata.remote_issues[0], title="New Title", description="Ha ha!"
    )
    tasks.sync_all_issues()
    helpdesk_testdata.issue1.refresh_from_db()
    assert (
        helpdesk_testdata.issue1.cached_title == "New Title"
        and helpdesk_testdata.issue1.cached_description == "Ha ha!"
    )


def test_sync_all_comments(helpdesk_testdata):
    gl = helpdesk_testdata.gl
    gl.edit_comment(helpdesk_testdata.remote_comment1, "I'm new!")
    tasks.sync_all_comments()
    helpdesk_testdata.comment1.refresh_from_db()
    assert helpdesk_testdata.comment1.cached_body == "I'm new!"


def test_import_new_issues(helpdesk_testdata):
    gl = helpdesk_testdata.gl
    new_issue = gl.create_issue(
        title="I'm a lost lambkin", description="Can you find my way home?"
    )
    tasks.import_new_issues(default_creator=helpdesk_testdata.gamer1.user)
    issue = models.IssueLink.objects.get(external_id=new_issue.iid)
    assert (
        issue
        and issue.cached_title == new_issue.title
        and issue.cached_description == new_issue.description
        and issue.cached_status == new_issue.state
        and issue.external_id == str(new_issue.iid)
        and issue.sync_status == "sync"
    )
    tasks.delete_remote_issue(issue)
