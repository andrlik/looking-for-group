import logging

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from ..game_catalog.utils import AbstractUUIDModel
from .backends import OperationError
from .signals import issue_state_changed
from .utils import get_backend_client, get_default_actor_for_syncs, is_system_comment

logger = logging.getLogger("helpdesk")

# Create your models here.

ISSUE_STATUS_CHOICES = (("opened", _("Open")), ("closed", _("Closed")))

SYNC_STATUS_CHOICES = (
    ("pending", _("Pending creation in remote repo")),
    ("pending_err", _("Remote creation failed. Awaiting next try.")),
    ("updating", _("Pending updates to push to remote repo")),
    ("updating_err", _("Update failed. Awaiting next try.")),
    ("closing", _("In process of closing remote ticket")),
    ("close_err", _("Close failed, awaiting next try")),
    ("deleting", _("In process of deleting remote ticket.")),
    ("delete_err", _("Deletion failed. Awaiting next try.")),
    ("deleted", _("Deleted object awaiting local copy deletion.")),
    ("reopen", _("Reopening remote ticket")),
    ("reopen_err", _("Reopen failed. Awaiting next try.")),
    ("sync", _("In Sync")),
)


class SyncInProgressException(Exception):
    pass


class IssueLink(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    A filed issue.
    """

    source_type = models.CharField(max_length=25, default="gitlab", db_index=True)
    external_id = models.CharField(
        max_length=25, db_index=True, unique=True, null=True, blank=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues_created",
        help_text=_(
            "The LFG user that created this. If not specified, you should display it as simple an anonymous admin user."
        ),
    )
    cached_status = models.CharField(
        max_length=25,
        default="opened",
        choices=ISSUE_STATUS_CHOICES,
        verbose_name=_("Status"),
    )
    cached_title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Title"),
        help_text=_("Title for the issue."),
    )
    cached_description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Descrition of the issue. Please be as detailed as possible."),
    )
    cached_comment_count = models.IntegerField(default=0)
    external_url = models.URLField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=15, default="pending", choices=SYNC_STATUS_CHOICES, db_index=True
    )
    last_sync = models.DateTimeField(default=timezone.now)
    subscribers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="subscribed_issues"
    )

    def __str__(self):
        return "#{}: {}".format(self.external_id, self.cached_title)

    def get_absolute_url(self):
        if self.external_id:
            return reverse_lazy(
                "helpdesk:issue-detail", kwargs={"ext_id": self.external_id}
            )
        else:
            return reverse_lazy("helpdesk:pending-issue", kwargs={"pk": self.id})

    def get_external_issue(self, lazy=False, backend_object=None):
        """
        Fetch the external issue through the backend. We cache the result to prevent hitting the API too hard.
        :param backend_object: An existing backend object. If not supplied, a one-off version will be created.
        :return: The external issue object
        :rtype: :class:`gitlab.v4.objects.ProjectIssue`
        """
        if not self.external_id or (not lazy and self.sync_status != "sync"):
            logger.debug(
                "This object is still syncing. Wait for it to be finished before retrieving."
            )
            raise SyncInProgressException(
                "This object is still syncing. Wait for it to be finished before retrieving."
            )
        if not backend_object:
            backend_object = get_backend_client()
        if lazy:
            return backend_object.get_issue(self.external_id, lazy=lazy)
        return cache.get_or_set(
            "helpdesk-{}".format(self.external_id),
            backend_object.get_issue(self.external_id),
            30,
        )

    def get_external_comments(self, backend_object=None):
        """
        Fetch the list of comments from the remote issue.

        :param backend_object: The backend instance to use. One will be created if not specified.
        :return: A list of :class:`gitlab.v4.objects.ProjectIssueNote` objects
        :rtype: list
        """
        if self.sync_status == "pending" or not self.external_id:
            logger.debug("This object is still being created. Wait until finished.")
            return None
        if not backend_object:
            backend_object = get_backend_client()
        try:
            comments = cache.get_or_set(
                "helpdesk-{}-comments".format(self.external_id),
                backend_object.get_issue_comments(
                    self.get_external_issue(lazy=True, backend_object=backend_object)
                ),
                30,
            )
        except SyncInProgressException:
            return None
        return comments

    def sync_with_source(self, backend_object=None):
        """
        Sync the cached data to be current with the master backend record.

        :param backend_object: An existing backend object. If not supplied, a one-off version will be created.
        :return: Whether the cache was updated
        :rtype: bool
        """
        logger.debug(
            "Starting sync for issue link with external id of {}...".format(
                self.external_id
            )
        )
        if not backend_object:
            backend_object = get_backend_client()
        try:
            issue = self.get_external_issue(backend_object=backend_object)
        except OperationError as oe:  # pragma: no cover
            logger.debug(
                "Operation error was raised trying to sync issue with external id {}. Message was: {}".format(
                    self.external_id, str(oe)
                )
            )
        except SyncInProgressException:
            return False
        updated = False
        if (
            self.cached_status != issue.state
            or self.cached_title != issue.title
            or self.cached_description != issue.description
        ):
            if self.cached_status != issue.state:
                issue_state_changed.send(
                    self,
                    issue=self,
                    user=get_default_actor_for_syncs(),
                    old_status=self.cached_status,
                    new_status=issue.state,
                )
            self.cached_status = issue.state
            self.cached_title = issue.title
            self.cached_description = issue.description
            logger.debug("updating core data.")
            updated = True
        if issue.user_notes_count != self.cached_comment_count:
            logger.debug("Updating comment count...")
            self.cached_comment_count = issue.user_notes_count
            updated = True
        self.last_sync = timezone.now()
        self.save()
        logger.debug(
            "Sync of issue link with external id {} complete!".format(self.external_id)
        )
        return updated


class IssueCommentLink(TimeStampedModel, AbstractUUIDModel, models.Model):
    """
    Linking a comment on a remote issue to the internal user.
    """

    source_type = models.CharField(max_length=25, default="gitlab", db_index=True)
    master_issue = models.ForeignKey(
        "IssueLink", on_delete=models.CASCADE, related_name="comments"
    )
    external_id = models.CharField(
        max_length=50, db_index=True, null=True, blank=True, unique=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_(
            "Which LFG user created this comment. If this is set to null it should be displayed as some sort of anonymous user."
        ),
    )
    cached_body = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Body"),
        help_text=_("Enter your comment."),
    )
    system_comment = models.BooleanField(default=False)
    sync_status = models.CharField(
        max_length=15, default="pending", choices=SYNC_STATUS_CHOICES, db_index=True
    )
    last_sync = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "Issue #{}/Comment #{}".format(
            self.master_issue.external_id, self.external_id
        )

    def get_external_comment(self, lazy=False, backend_object=None):
        """
        Grab the remote object. We cache this value so that we don't slam the Gitlab API.

        :param backend_object: The backend connector to use. If not specified, one will be created.
        :return: The comment as a single object.
        :rtype: :class:`gitlab.v4.objects.ProjectIssueNote`
        """
        if self.sync_status == "pending" or not self.external_id:
            raise SyncInProgressException(
                "This comment is currently awaiting pushing data to the backend. Please wait until a worker finishes."
            )
        if not backend_object:
            backend_object = get_backend_client()
        try:
            issue = self.master_issue.get_external_issue(
                lazy=True, backend_object=backend_object
            )
        except SyncInProgressException:
            logger.debug(
                "The issue is still being synced. You'll need to rely on cached values until finished."
            )
            raise SyncInProgressException(
                "The issue is still being synced. You'll need to rely on cached values until finished."
            )
        if lazy:
            comment = backend_object.get_issue_comment(
                issue, self.external_id, lazy=lazy
            )
        else:
            try:
                comment = cache.get_or_set(
                    "helpdesk-{}-comment-{}".format(
                        self.master_issue.external_id, self.external_id
                    ),
                    backend_object.get_issue_comment(issue, self.external_id),
                    30,
                )
            except OperationError:  # pragma: no cover
                logger.error(
                    "There was an error retriveing the value for comment {} from Gitlab.".format(
                        self.id
                    )
                )
                return None
        return comment

    def sync_with_source(self, backend_object=None):
        """
        Sync the cached data to be current with the master backend record.

        :param backend_object: An existing backend object. If not supplied, a one-off version will be created.
        :return: Whether the cache was updated.
        :rtype: bool
        """
        logger.debug(
            "Starting sync of comment with external id {} from issue with external id {}...".format(
                self.external_id, self.master_issue.external_id
            )
        )
        if not backend_object:
            backend_object = get_backend_client()
        try:
            external_comment = self.get_external_comment(backend_object=backend_object)
        except SyncInProgressException as se:
            logger.debug(str(se))
            return False
        if not external_comment:
            return False
        updated = False
        if self.cached_body != external_comment.body or external_comment.body.strip() in [
            "reopened",
            "closed",
        ]:
            if external_comment.body.strip() == "reopened":
                self.cached_body = "Reopened this issue."
            elif external_comment.body.strip() == "closed":
                self.cached_body = "Closed this issue."
            else:
                self.cached_body = external_comment.body
            updated = True
        if is_system_comment(external_comment) != self.system_comment:
            self.system_comment = is_system_comment(external_comment)
            updated = True
        self.last_sync = timezone.now()
        self.save()
        logger.debug(
            "Comment sync complete for external id {} from issue with with external id {}!".format(
                self.external_id, self.master_issue.external_id
            )
        )
        return updated
