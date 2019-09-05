import pytest
from django.conf import settings

from ..backends.gitlab import GitlabConnector
from ..utils import get_backend_client


@pytest.fixture
def gl():
    return get_backend_client()


@pytest.fixture
def test_issues(gl):
    issue1 = gl.create_issue(title="Monkey", description="test this stuff")
    issue2 = gl.create_issue(title="Test 2", description="Another test!")
    issue_list = [issue1, issue2]
    yield issue_list
    issue1.delete()
    issue2.delete()


def test_gitlab_init():
    gl = GitlabConnector(
        gitlab_url=settings.GITLAB_URL,
        personal_token=settings.GITLAB_TOKEN,
        project=settings.GITLAB_PROJECT_ID,
    )
    assert gl.project


def test_backend_fetcher():
    gl = get_backend_client()
    assert gl.project.id == settings.GITLAB_PROJECT_ID


def test_create_issue(gl):
    issue = gl.create_issue(title="Monkey", description="test this stuff")
    assert issue.iid
    issue.delete()


def test_list_issues(gl, test_issues):
    issue_list = gl.get_issues()
    assert issue_list
    for x in test_issues:
        assert x in issue_list


def test_list_specific_issues(gl, test_issues):
    issue_list = gl.get_issues(issue_id_list=[test_issues[0].iid])
    assert len(issue_list) == 1
    assert test_issues[0] == issue_list[0]


def test_get_issue(gl, test_issues):
    for x in test_issues:
        issue = gl.get_issue(x.iid)
        assert issue.title == x.title


def test_edit_issue(gl, test_issues):
    for x in test_issues:
        gl.edit_issue(x, title="New sexy title", description="New sexy description")
        assert gl.get_issue(x.iid).title == "New sexy title"


def test_comment_issue(gl, test_issues):
    issue = test_issues[0]
    comment = gl.comment_on_issue(issue, "Don't you think this is a little extreme?")
    assert comment.id
    comments = gl.get_issue_comments(issue)
    assert comment in comments
    assert gl.get_issue_comment(issue, comment.id)


def test_update_comment(gl, test_issues):
    issue = test_issues[0]
    comment = gl.comment_on_issue(issue, "Don't you think this ia a bit much?")
    gl.edit_comment(comment, "Let's wrap this up, eh?")
    assert gl.get_issue_comment(issue, comment.id).body == "Let's wrap this up, eh?"


def test_delete_comment(gl, test_issues):
    issue = test_issues[0]
    comment = gl.comment_on_issue(issue, "Don't you think this ia a bit much?")
    gl.delete_comment(comment)
    comments = gl.get_issue_comments(issue)
    assert comment not in comments


def test_close_issue_without_comment(gl, test_issues):
    issue = test_issues[0]
    new_issue, comment = gl.close_issue(issue)
    assert not comment
    assert gl.get_issue(issue.iid).state == "closed"


def test_close_issue_with_comment(gl, test_issues):
    issue = test_issues[0]
    new_issue, comment = gl.close_issue(issue, "Shut it down!")
    assert gl.get_issue(issue.iid).state == "closed"
    assert comment in gl.get_issue_comments(issue)


def test_reopen_issue(gl, test_issues):
    issue = test_issues[0]
    gl.close_issue(issue)
    assert gl.get_issue(issue.iid).state == "closed"
    gl.reopen_issue(issue)
    assert gl.get_issue(issue.iid).state == "opened"
