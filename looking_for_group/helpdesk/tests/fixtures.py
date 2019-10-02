import pytest
from django.contrib.contenttypes.models import ContentType

from ...gamer_profiles.tests.factories import GamerProfileFactory
from .. import models
from ..utils import create_issuelink_from_remote_issue, get_backend_client

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def gl():
    return get_backend_client()


@pytest.fixture
def test_issues(gl):
    issue1 = gl.create_issue(title="Monkey", description="test this stuff")
    issue2 = gl.create_issue(title="Test 2", description="Another test!")
    issue3 = gl.create_issue(title="Test 3", description="A third test")
    issue_syncer = gl.create_issue(title="Always pending sync", description="Yup")
    issue_list = [issue1, issue2, issue3, issue_syncer]
    yield issue_list
    issue1.delete()
    issue2.delete()
    issue3.delete()
    issue_syncer.delete()


class IssueTData(object):
    """
    An object to quickly initialize a test envirnoments for the
    helpdesk.
    """

    def __init__(self, remote_issues, backend_client=None, *args, **kwargs):
        if not backend_client:
            backend_client = get_backend_client()
        self.gl = backend_client
        self.super_gamer = GamerProfileFactory()
        self.super_gamer.user.is_superuser = True
        self.super_gamer.user.save()
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.issue1 = create_issuelink_from_remote_issue(
            remote_issues[0], creator=self.gamer1.user, backend_client=backend_client
        )
        self.issue2 = create_issuelink_from_remote_issue(
            remote_issues[1], creator=self.gamer2.user, backend_client=backend_client
        )
        self.issue3 = create_issuelink_from_remote_issue(
            remote_issues[2], creator=self.gamer3.user, backend_client=backend_client
        )
        self.issue4 = models.IssueLink.objects.create(
            cached_title="This is an unsent issue",
            cached_description="I'm just messing around.",
            sync_status="pending",
            creator=self.gamer1.user,
        )
        self.issue_syncer = create_issuelink_from_remote_issue(
            remote_issues[3], creator=self.gamer3.user, backend_client=backend_client
        )
        self.issue_syncer.sync_status = "updating"
        self.issue_syncer.save()
        self.remote_comment1 = self.gl.comment_on_issue(
            remote_issues[0], "I like this thing. Please fix it."
        )
        self.comment1 = models.IssueCommentLink.objects.create(
            master_issue=self.issue1,
            creator=self.gamer2.user,
            cached_body=self.remote_comment1.body,
            external_id=self.remote_comment1.id,
            sync_status="sync",
        )
        self.remote_comment2 = self.gl.comment_on_issue(remote_issues[0], "I agree!")
        self.comment2 = models.IssueCommentLink.objects.create(
            master_issue=self.issue1,
            creator=self.gamer3.user,
            cached_body=self.remote_comment2.body,
            external_id=self.remote_comment2.id,
            sync_status="sync",
        )
        self.remote_comment3 = self.gl.comment_on_issue(
            remote_issues[1], "This is neat!"
        )
        self.comment3 = models.IssueCommentLink.objects.create(
            master_issue=self.issue2,
            creator=self.gamer1.user,
            cached_body=self.remote_comment3.body,
            external_id=self.remote_comment3.id,
            sync_status="sync",
        )
        self.comment4 = models.IssueCommentLink.objects.create(
            master_issue=self.issue3,
            creator=self.gamer3.user,
            cached_body="Hi, I am pending comment",
            sync_status="pending",
        )
        self.remote_comment5 = self.gl.comment_on_issue(
            remote_issues[3], "Hi, I am a synced comment on an updating issue"
        )
        self.comment5 = models.IssueCommentLink.objects.create(
            master_issue=self.issue_syncer,
            creator=self.gamer3.user,
            cached_body="Hi, I am a synced comment on an updating issue",
            sync_status="sync",
            external_id=self.remote_comment5.id,
        )
        self.remote_comment_gl = self.gl.comment_on_issue(
            remote_issues[1], "We're working on this right now."
        )  # Should not be replicated in database to test display with no matching comment link.
        self.remote_issues = remote_issues


@pytest.fixture
def helpdesk_testdata(gl, test_issues):
    yield IssueTData(test_issues, backend_client=gl)
    ContentType.objects.clear_cache()
