import logging
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from notifications.signals import notify

from . import models
from .backends import OperationError
from .utils import create_issuelink_from_remote_issue, get_backend_client, get_default_actor_for_syncs

logger = logging.getLogger("helpdesk")


def create_remote_issue(issuelink):
    """
    Try to create the remote issue, and updates the issue link with the external data.

    :param issuelink: The issue link to use.
    :type issuelink: :class:`looking_for_group.helpdesk.models.IssueLink`
    """
    if issuelink.sync_status != "pending":
        issuelink.sync_status = "pending"
        issuelink.save()
    gl = get_backend_client()
    try:
        issue = gl.create_issue(
            title=issuelink.cached_title, description=issuelink.cached_description
        )
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "Tried to create remote issue, but got an operational error. Will try again later. Mesage was: {}".format(
                str(oe)
            )
        )
        issuelink.sync_status = "pending_err"
        issuelink.save()
        return
    issuelink.external_id = issue.iid
    issuelink.external_url = issue.web_url
    issuelink.sync_status = "sync"
    issuelink.last_sync = timezone.now()
    issuelink.save()
    cache.set("helpdesk-{}".format(issuelink.external_id), issue, 30)


def update_remote_issue(issuelink):
    """
    Update the remote issue to match the new records in the issue.

    :param issuelink: The issue link for the corresponding external issue.
    :type issuelink: :class:`looking_for_group.helpdesk.models.IssueLink`
    """
    if issuelink.sync_status == "pending" or not issuelink.external_id:
        logger.debug(
            "Was asked to update an issue, but the remote issue isn't created yet. Skipping.."
        )
        return
    if issuelink.sync_status != "updating":
        issuelink.sync_status = "updating"
        issuelink.save()
    try:
        gl = get_backend_client()
        issue = issuelink.get_external_issue(lazy=True, backend_object=gl)
        new_issue = gl.edit_issue(
            issue,
            title=issuelink.cached_title,
            description=issuelink.cached_description,
        )
    except OperationError:  # pragma: no cover
        logger.error(
            "There was an error trying to send the new data to github. Leaving it in updating state until a worker can resolve."
        )
        issuelink.sync_status = "update_err"
        issuelink.save()
        return
    issuelink.sync_status = "sync"
    issuelink.last_sync = timezone.now()
    issuelink.save()
    cache.set("helpdesk-{}".format(issue.iid), new_issue, 30)


def delete_remote_issue(issuelink):
    """
    Delete the remote issue to match the new records in the issue.

    :param issuelink: The issue link for the corresponding external issue.
    :type issuelink: :class:`looking_for_group.helpdesk.models.IssueLink`
    """
    if issuelink.sync_status not in ["sync", "deleting", "delete_err"]:
        logger.debug("Was asked to delete a record that is currently syncing. Skpping.")
        return
    issuelink.sync_status = "deleting"
    issuelink.save()
    try:
        gl = get_backend_client()
        issue = issuelink.get_external_issue(lazy=True, backend_object=gl)
        issue.delete()
        issuelink.external_id = None
        issuelink.external_url = None
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "Error encountered when deleteing issue. Leeting another worker take care of it later. Message was: {}".format(
                str(oe)
            )
        )
        issuelink.sync_status = "delete_err"
        issuelink.save()
        return
    issuelink.sync_status = "deleted"
    issuelink.last_sync = timezone.now()
    issuelink.save()


def close_remote_issue(issuelink, comment_text=None):
    """
    Update the status of the remote issue according to the status within the given issuelink.

    :param issuelink: The model instance to use.
    :type issuelink: :class:`looking_for_group.helpdesk.models.IssueLink`
    :param comment_text: The text to be used as the comment for closing.
    :type comment_text: string or None
    """
    if issuelink.sync_status not in ["sync", "close_err"] or not issuelink.external_id:
        logger.debug(
            "Was asked to change an issue status, but the remote issue isn't created yet. Skipping..."
        )
        return
    logger.debug(
        "Begining attempt to close remote issue {}".format(issuelink.external_id)
    )
    issuelink.sync_status = "closing"
    issuelink.save()
    try:
        gl = get_backend_client()
        issue = issuelink.get_external_issue(lazy=True, backend_object=gl)
        new_issue, note = gl.close_issue(issue, comment_text=comment_text)
        if note:
            models.IssueCommentLink.objects.create(
                external_id=note.id,
                master_issue=issuelink,
                cached_body=comment_text,
                sync_status="sync",
            )
        cache.set("helpdesk-{}".format(issuelink.external_id), new_issue, 30)
        if issuelink.cached_status != "closed":
            logger.debug("Local issue copy wasn't set to closed yet... updating.")
            issuelink.cached_status = "closed"
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "There was an error trying to update the issue. Will try again later. Error message was: {}".format(
                str(oe)
            )
        )
        issuelink.sync_status = "close_err"
        issuelink.save()
        return
    logger.debug("Successfully closed remote issue.")
    issuelink.sync_status = "sync"
    issuelink.save()


def queue_issue_for_sync(issuelink):
    issuelink.sync_with_source()


def reopen_remote_issue(issuelink):
    """
    Update the status of the remote issue according to the status within the given issuelink.

    :param issuelink: The model instance to use.
    :type issuelink: :class:`looking_for_group.helpdesk.models.IssueLink`
    """
    if issuelink.sync_status not in ["sync", "reopen_err"] or not issuelink.external_id:
        logger.debug(
            "Was asked to change an issue status, bu tth eremote issue isn't created yet. Skipping..."
        )
        return
    issuelink.sync_status = "reopen"
    issuelink.save()
    try:
        gl = get_backend_client()
        issue = issuelink.get_external_issue(lazy=True, backend_object=gl)
        new_issue = gl.reopen_issue(issue)
        cache.set("helpdesk-{}".format(issuelink.external_id), new_issue, 30)
        if issuelink.cached_status != "opened":
            logger.debug(
                "This issue didn't already have it's cached status set to opened. Doing so now."
            )
            issuelink.cached_status = "opened"
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "There was an error trying to update the issue. Will try again later. Error message was: {}".format(
                str(oe)
            )
        )
        issuelink.sync_status = "reopen_err"
        issuelink.save()
        return
    issuelink.sync_status = "sync"
    issuelink.save()


def create_remote_comment(commentlink):
    """
    Create a remote comment based on the submitted comment link info.

    :param commentlink: The Django model instance of the comment link
    :type commentlink: :class:`looking_for_group.helpdesk.models.IssueCommentLink`
    """
    logger.debug(
        "Starting to create remote comment for comment id {}".format(commentlink.id)
    )
    commentlink.sync_status = "pending"
    commentlink.save()
    gl = get_backend_client()
    try:
        issue = commentlink.master_issue.get_external_issue(
            lazy=True, backend_object=gl
        )
        new_comment = gl.comment_on_issue(issue, commentlink.cached_body)
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "Could not create remote comment from {}. Will try again later. Message was: {}".format(
                commentlink.id, str(oe)
            )
        )
        commentlink.sync_status = "pending_err"
        commentlink.save()
        return
    commentlink.external_id = new_comment.id
    commentlink.last_sync = timezone.now()
    commentlink.sync_status = "sync"
    commentlink.save()


def update_remote_comment(commentlink):
    """
    Update a remote comment with the new body from the updated link object.

    :param commentlink: The Django model instance of the comment link
    :type commentlink: :class:`looking_for_group.helpdesk.models.IssueCommentLink`
    """
    if commentlink.sync_status not in ["sync", "update_err"]:
        logger.debug(
            "We were asked to update a comment that's already syncing. Try again later."
        )
        return
    logger.debug("Starting update of remote comment {}".format(commentlink.external_id))
    commentlink.sync_status = "updating"
    commentlink.save()
    gl = get_backend_client()
    try:
        comment = commentlink.get_external_comment(lazy=True, backend_object=gl)
        new_comment = gl.edit_comment(comment, commentlink.cached_body)
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "Could not update remote comment with external id {}. Will try again later. Message was: {}".format(
                commentlink.external_id, str(oe)
            )
        )
        commentlink.sync_status = "updating_err"
        commentlink.save()
        return
    except models.SyncInProgressException:
        logger.debug("Cannot update remote comment that's issue is still syncing.")
    commentlink.last_sync = timezone.now()
    commentlink.sync_status = "sync"
    commentlink.save()
    cache.set(
        "helpdesk-{}-comment-{}".format(
            commentlink.master_issue.external_id, commentlink.external_id
        ),
        new_comment,
        30,
    )


def delete_remote_comment(commentlink):
    """
    Delete the remote comment associated with this object and clear the external id

    :param commentlink: The comment link object tied to the remote comment.
    :type commentlink: :class:`looking_for_group.helpdesk.models.IssueCommentLink`
    """
    if commentlink.sync_status not in ["sync", "delete_err"]:
        logger.debug(
            "We were asked to delete a comment that still has pending sync tasks. Try again later."
        )
        return
    logger.debug(
        "Beginning delettion of remote comment {}".format(commentlink.external_id)
    )
    commentlink.sync_status = "deleting"
    commentlink.save()
    gl = get_backend_client()
    try:
        comment = commentlink.get_external_comment(lazy=True, backend_object=gl)
        comment.delete()
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "Could not delete remote comment with external id {}. Will try again later. Message was: {}".format(
                commentlink.external_id, str(oe)
            )
        )
        commentlink.sync_status = "delete_err"
        commentlink.save()
        return
    except models.SyncInProgressException:
        logger.debug(
            "The comment or its issue are currently still pending another sync task. Will try gain later."
        )
        commentlink.sync_status = "delete_err"
        commentlink.save()
        return
    commentlink.external_id = None
    commentlink.sync_status = "deleted"
    commentlink.save()


def sync_all_issues(sync_closed=False):
    """
    Go through all the linked issues and run their native sync method. Creates a reusable
    backend connection object to reduce memory usage.

    :param sync_closed: Should we both syncing issues that we know to be closed over two weeks ago?
    :type sync_closed: bool
    """
    logger.debug("Starting batch issue sync with sync_closed as {}".format(sync_closed))
    updated_records = 0
    gl = get_backend_client()
    issues = models.IssueLink.objects.filter(sync_status="sync")
    if not sync_closed:
        issues = issues.exclude(
            cached_status="closed", last_sync__lte=timezone.now() - timedelta(days=14)
        )
    for il in issues:
        updated = il.sync_with_source(backend_object=gl)
        if updated:
            updated_records += 1
    logger.debug("Sync finished with {} issue records updated.".format(updated_records))


def sync_all_comments(sync_closed=False):
    """
    Go through all the comments and sync the cache from the server.

    :param sync_closed: Should we sync comments from issues closed more than two weeks ago?
    :type sync_closed: bool
    """
    logger.debug(
        "Starting batch issue comment sync with sync_closed as {}".format(sync_closed)
    )
    updated_records = 0
    gl = get_backend_client()
    comments = models.IssueCommentLink.objects.filter(
        sync_status="sync"
    ).select_related("master_issue")
    if not sync_closed:
        comments = comments.exclude(
            master_issue__cached_status="closed",
            master_issue__last_sync__lte=timezone.now() - timedelta(days=14),
        )
    for cl in comments:
        updated = cl.sync_with_source(backend_object=gl)
        if updated:
            updated_records += 1
    logger.debug("Sync finished with {} comments updated.".format(updated_records))


def import_new_issues(sync_closed=False, default_creator=None):
    """
    Bring in unsynced issues that did not originate from this instance.

    :param sync_closed: Should we import missing closed issues or omit them.
    :param default_creator: The user to associate with this record if any. Must be an instance of settings.AUTH_USER_MODEL or set as None
    :type sync_closed: bool
    """
    logger.debug("Beginning import of issues from backend...")
    if not default_creator:
        default_creator = get_default_actor_for_syncs()
    new_issues = 0
    new_closed_issues = 0
    gl = get_backend_client()
    # ids_to_exclude = [il.external_id for il in models.IssueLink.objects.all()]
    try:
        issues_to_import = gl.get_issues()
        for issue in issues_to_import:
            try:
                models.IssueLink.objects.get(external_id=issue.iid)
            except ObjectDoesNotExist:
                logger.debug(
                    "New issue found with external id of {}. Creating link...".format(
                        issue.iid
                    )
                )
                create_issuelink_from_remote_issue(
                    issue, creator=default_creator, backend_client=gl
                )
                new_issues += 1
        logger.debug("Created {} new issue links for open issues.".format(new_issues))
        if sync_closed:
            logger.debug(
                "Running with sync_closed, so doing an additional import of closed issues."
            )
            issues_to_import = gl.get_issues(filter_status="closed")
            for issue in issues_to_import:
                try:
                    models.IssueLink.objects.get(external_id=issue.iid)
                except ObjectDoesNotExist:
                    logger.debug(
                        "Found a new closed issue with external id of {}. Creating link...".format(
                            issue.iid
                        )
                    )
                    create_issuelink_from_remote_issue(
                        issue, creator=default_creator, backend_client=gl
                    )
                    new_closed_issues += 1
            logger.debug(
                "Created {} new issue links for closed issues.".format(
                    new_closed_issues
                )
            )
        logger.debug(
            "Import complete with {} total new issue links.".format(
                new_issues + new_closed_issues
            )
        )
    except OperationError as oe:  # pragma: no cover
        logger.error(
            "An operation error was raised when trying to import records. Message was: {}".format(
                str(oe)
            )
        )


def notify_subscribers_of_new_comment(comment):
    """
    Send notifications to all the subscribers of an issue that a new comment was added.
    """
    recipients = comment.master_issue.subscribers.all()
    notify.send(
        comment.creator,
        recipient=recipients,
        verb="commented on",
        action_object=comment.master_issue,
    )


def notify_subscribers_of_issue_state_change(issue, user, old_status, new_status):
    """
    Send notifications to all the subscribers of an issue that an issue changed state was added.
    """
    logger.debug("Running debug query...")
    logger.debug(
        "Checking to see if issue is the right kind of object... {}".format(
            isinstance(issue, models.IssueLink)
        )
    )
    logger.debug(
        "Testing is issue has the subscribers attribute... {}".format(
            hasattr(issue, "subscribers")
        )
    )
    logger.debug(
        "Checking that subscribers is the right type... Type = {}".format(
            type(issue.subscribers)
        )
    )
    logger.debug(
        "Checking that the subscribers queryset is what is expected... Type of {} for object {}".format(
            type(issue.subscribers.all()), issue.subscribers.all()
        )
    )
    logger.debug(str(len(issue.subscribers.all())))
    logger.debug("Notifying subscribers of issue state change. Fetching subscribers...")
    if issue.subscribers.all().count() == 0:
        logger.debug("There are no subscribers to this issue.")
    else:
        recipients = issue.subscribers.all()
        logger.debug("Subscribers fetched...")
        logger.debug(
            "Notifying {} subscribers of issue state change.".format(len(recipients))
        )
        verb = "closed issue"
        if new_status == "opened" and old_status == "closed":
            verb = "reopened issue"
        notify.send(user, recipient=recipients, verb=verb, action_object=issue)
        logger.debug("Successfully sent notifications!")
