import pytest

from .. import models

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "issueobject,success_expected",
    [("issue1", True), ("issue2", True), ("issue3", True), ("issue4", False)],
)
def test_fetch_remote_issue(helpdesk_testdata, issueobject, success_expected):
    """
    Test that an issue can appropriately fetch it's remote counterpart.
    """
    local_issue = getattr(helpdesk_testdata, issueobject)
    if not success_expected:
        with pytest.raises(models.SyncInProgressException):
            local_issue.get_external_issue(backend_object=helpdesk_testdata.gl)
    else:
        remote_issue = local_issue.get_external_issue(
            backend_object=helpdesk_testdata.gl
        )
        assert remote_issue.iid
        assert remote_issue.title == local_issue.cached_title


@pytest.mark.parametrize(
    "issueobject,remote_issue_index,change_remote,expected_result",
    [
        ("issue1", "0", True, True),
        ("issue2", "1", False, True),  # Comments were added.
        ("issue3", "2", True, True),
        ("issue4", None, False, False),
    ],
)
def test_issue_sync_with_source(
    helpdesk_testdata, issueobject, remote_issue_index, change_remote, expected_result
):
    """
    Test sync from source method and expected results.
    """
    local_issue = getattr(helpdesk_testdata, issueobject)
    new_issue = None
    gl = helpdesk_testdata.gl
    if remote_issue_index:
        remote_issue = getattr(helpdesk_testdata, "remote_issues")[
            int(remote_issue_index)
        ]
    else:
        remote_issue = None

    if change_remote:
        new_issue = gl.edit_issue(
            remote_issue,
            title="Let's make tests a little different",
            description="New and improved",
        )
    assert expected_result == local_issue.sync_with_source(backend_object=gl)
    local_issue.refresh_from_db()
    if new_issue:
        assert new_issue.description == local_issue.cached_description


@pytest.mark.parametrize(
    "issueobject,retrieve_success,list_of_expected_remote_comment_names",
    [
        ("issue1", True, ["remote_comment1", "remote_comment2"]),
        ("issue2", True, ["remote_comment3", "remote_comment_gl"]),
        ("issue3", False, []),  # An empty list is the same as nothing to python.
        ("issue4", False, []),
    ],
)
def test_get_remote_issue_comments(
    helpdesk_testdata,
    issueobject,
    retrieve_success,
    list_of_expected_remote_comment_names,
):
    """
    Try to use the model method to retrive the remote comments and then verify the expected comments are present in the list.
    """
    local_issue = getattr(helpdesk_testdata, issueobject)
    gl = helpdesk_testdata.gl
    expected_comments = [
        getattr(helpdesk_testdata, cname)
        for cname in list_of_expected_remote_comment_names
    ]
    comments = local_issue.get_external_comments(backend_object=gl)
    if not retrieve_success:
        assert not comments
    else:
        assert comments
        if len(list_of_expected_remote_comment_names) > 0:
            for c in expected_comments:
                assert c in comments


@pytest.mark.parametrize(
    "commentname,success_expected",
    [("comment1", True), ("comment2", True), ("comment3", True), ("comment4", False)],
)
def test_retrieve_external_comment(helpdesk_testdata, commentname, success_expected):
    """
    Test fetching an external comment from remote.
    """
    local_comment = getattr(helpdesk_testdata, commentname)
    gl = helpdesk_testdata.gl
    if not success_expected:
        with pytest.raises(models.SyncInProgressException):
            local_comment.get_external_comment(backend_object=gl)
    else:
        remote_comment = local_comment.get_external_comment(backend_object=gl)
        assert remote_comment
        assert remote_comment.body == local_comment.cached_body


@pytest.mark.parametrize(
    "commentname,remote_comment_name,change_source,update_expected",
    [
        ("comment1", "remote_comment1", True, True),
        ("comment2", "remote_comment2", True, True),
        ("comment3", "remote_comment3", False, False),
        ("comment4", None, False, False),
        ("comment5", "remote_comment5", False, False),
    ],
)
def test_comment_sync_with_source(
    helpdesk_testdata, commentname, remote_comment_name, change_source, update_expected
):
    new_comment = None
    local_comment = getattr(helpdesk_testdata, commentname)
    gl = helpdesk_testdata.gl
    if remote_comment_name:
        remote_comment = getattr(helpdesk_testdata, remote_comment_name)
    else:
        remote_comment = None
    if change_source and remote_comment:
        new_comment = gl.edit_comment(remote_comment, "Eat a hot dog")
    assert update_expected == local_comment.sync_with_source(backend_object=gl)
    local_comment.refresh_from_db()
    if new_comment:
        assert local_comment.cached_body == new_comment.body
