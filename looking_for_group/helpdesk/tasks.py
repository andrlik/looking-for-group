import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from . import models
from .backends import OperationError
from .utils import create_issuelink_from_remote_issue, get_backend_client

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
    except OperationError as oe:
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
        issue = issuelink.get_external_issue(backend_object=gl)
        new_issue = gl.update_issue(
            issue,
            title=issuelink.cached_title,
            description=issuelink.cached_description,
        )
        cache.incr_version("helpdesk-{}".format(issue.iid))
    except OperationError as oe:
        logger.error(
            "There was an error trying to send the new data to github. Leaving it in updating state until a worker can resolve."
        )
        issuelink.sync_status = "update_err"
        issuelink.save()
        return
    issuelink.sync_status = "sync"
    issuelink.last_sync = timezone.now()
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
        issue = commentlink.master_issue.get_external_issue(backend_object=gl)
        new_comment = gl.comment_on_issue(issue, commentlink.cached_body)
    except OperationError as oe:
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
    logger.debug("Starting update of remote comment {}".format(commentlink.external_id))
    commentlink.sync_status = "updating"
    commentlink.save()
    gl = get_backend_client()
    try:
        comment = commentlink.get_external_comment(backend_object=gl)
        new_comment = gl.edit_comment(comment, commentlink.cached_body)
    except OperationError as oe:
        logger.error(
            "Could not update remote comment with external id {}. Will try again later. Message was: {}".format(
                commentlink.external_id, str(oe)
            )
        )
        commentlink.sync_status = "updating_err"
        commentlink.save()
        return
    commentlink.last_sync = timezone.now()
    commentlink.sync_status = "sync"
    commentlink.save()
    cache.incr_version(
        "helpdesk-{}-comment-{}".format(
            commentlink.master_issue.external_id, commentlink.external_id
        )
    )


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
        updated = il.sync_from_souce(backend_object=gl)
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
        updated = cl.sync_from_source(backend_object=gl)
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
    new_issues = 0
    new_closed_issues = 0
    gl = get_backend_client()
    ids_to_exclude = [il.external_id for il in models.IssueLink.objects.all()]
    try:
        issues_to_import = gl.get_issues()
        for issue in issues_to_import:
            if issue.iid not in ids_to_exclude:
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
                if issue.iid not in ids_to_exclude:
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
    except OperationError as oe:
        logger.error(
            "An operation error was raised when trying to import records. Message was: {}".format(
                str(oe)
            )
        )
