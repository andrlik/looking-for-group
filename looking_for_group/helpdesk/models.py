from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from game_catalog.utils import AbstractUUIDModel
from model_utils.models import TimeStampedModel

from .backends.base import OperationError
from .backends.gitlab import GitlabConnector

gl = GitlabConnector(
    gitlab_url=settings.GITLAB_URL,
    personal_token=settings.GITLAB_TOKEN,
    project=settings.GITLAB_PROJECT_ID,
)

# Create your models here.

ISSUE_STATUS_CHOICES = (("opened", _("Open")), ("closed", _("Closed")))


class IssueLink(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A filed issue.
    """

    source_type = models.CharField(max_length=25, default="gitlab", db_index=True)
    external_id = models.CharField(max_length=25, db_index=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cached_status = models.CharField(
        max_length=25, default="opened", choices=ISSUE_STATUS_CHOICES
    )
    cached_title = models.CharField(max_length=255, null=True, blank=True)
    cached_description = models.TextField(null=True, blank=True)
    external_url = models.URLField(null=True, blank=True)
    last_sync = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "#{}: {}".format(self.external_id, self.cached_title)

    def sync_with_source(self):
        try:
            issue = gl.project.issues.get(self.external_id)
        except OperationError:  # pragma: no cover
            pass
        if issue.updated_at > self.last_sync:
            self.cached_status = issue.state
            self.cached_title = issue.title
            self.cached_description = issue.description
            self.last_sync = timezone.now()
            self.save()


class IssueCommentLink(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Linking a comment on a remote issue to the internal user.
    """

    source_type = models.CharField(max_length=25, default="gitlab", db_index=True)
    master_issue = models.ForeignKey(IssueLink, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=50, db_index=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cached_body = models.TextField(null=True, blank=True)
    last_sync = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "Issue #{}/Comment #{}".format(
            self.master_issue.external_id, self.external_id
        )
