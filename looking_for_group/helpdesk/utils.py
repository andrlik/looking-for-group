import logging
from datetime import datetime

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from pytz import timezone as ptimezone

from . import models
from .backends import AuthenticationError, GitlabConnector, NotImplementedError

logger = logging.getLogger("helpdesk")


def get_backend_client(backend="gitlab"):
    """
    Return a backend implementation object with the authentication scheme.

    :param backend: Text key for the backend in question
    :type backend: string

    :return: The backend API object.
    :rtype: :class:`looking_for_group.backends.gitlab.GitlabConnector`
    """
    if backend != "gitlab":
        raise NotImplementedError("Only gitlab backends are currently supported.")
    try:
        connector = GitlabConnector(
            gitlab_url=settings.GITLAB_URL,
            personal_token=settings.GITLAB_TOKEN,
            project=settings.GITLAB_PROJECT_ID,
        )
    except AuthenticationError as ae:  # pragma: no cover
        logger.error(
            "Authentication error creating gitlab connector. Message was: {}".format(
                str(ae)
            )
        )
        logger.debug("Created valid gitlab connector and returning object.")
    return connector


def create_issuelink_from_remote_issue(remote_issue, creator=None, backend_client=None):
    """
    Take a remote issue object and create an issue link from it. If creator is specified, link it to that creator.

    :param remote_issue: The issue to link to.
    :param creator: The user to associate with the ticket. Must be an instance of `settings.AUTH_USER_MODEL`
    :param backend_client: An instance of the backend client to use. Will be created if not specified.
    :type remote_issue: :class:`gitlab.v4.objects.ProjectIssue`
    :type backend_client: :class:`looking_for_group.helpdesk.backends.GitlabConnector`
    :return: The IssueLink object
    :rtype: :class:`looking_for_group.helpdesk.models.IssueLink`
    """
    if not backend_client:  # pragma: no cover
        backend_client = get_backend_client()
    return models.IssueLink.objects.create(
        external_id=remote_issue.iid,
        creator=creator,
        cached_status=remote_issue.state,
        cached_title=remote_issue.title,
        cached_description=remote_issue.description,
        cached_comment_count=remote_issue.user_notes_count,
        external_url=remote_issue.web_url,
        sync_status="sync",
        created=datetime.strptime(
            remote_issue.created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=ptimezone("UTC")),
        modified=datetime.strptime(
            remote_issue.updated_at, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=ptimezone("UTC")),
    )


def reconcile_comments(issuelink, use_emails=True):
    """
    For a given issue link object, fetch both the remote comments from gitlab and the locally stored comments in the db and reconcile them against each other.
    Create a list of dicts representing the related comments.

    :param issuelink: The issuelink object to check against.
    :param use_emails: Should we try to reconcile authors of comments missing from the DB via email?
    :type issuelink: :class:`looking_for_group.helpdesk.models.IssueLink`
    :type use_emails: bool
    :return: A list of dicts representing the comments.
    :rtype: list
    """
    remote_comments = issuelink.get_external_comments()
    local_comments = issuelink.comments.all()
    local_comment_ids = [c.id for c in local_comments]
    if not remote_comments:
        return local_comments
    comments_to_return = []
    ids_to_exclude_from_local = []
    for comment in remote_comments:
        comm = {
            "external_id": comment.id,
            "body": comment.body,
            "db_version": None,
            "creator": None,
            "created": datetime.strptime(
                comment.created_at, "%Y-%m-%dT%H:%M:%S.%f"
            ).replace(tzinfo=ptimezone("UTC")),
            "modified": datetime.strptime(
                comment.updated_at, "%Y-%m-%dT%H:%M:%S.%f"
            ).replace(tzinfo=ptimezone("UTC")),
        }
        if comment.id in local_comment_ids:
            lcom = local_comments.get(external_id=comment.id)
            comm["db_version"] = lcom
            comm["creator"] = lcom.creator
            comm["body"] = lcom.cached_body
        if not comm["db_version"] and use_emails:
            # TODO: Try and reconcile against a user via email address.
            try:
                user = EmailAddress.objects.get(email=comm.author.email).user
                comm["creator"] = user
                new_local = models.IssueCommentLink.objects.create(
                    external_id=comment.id,
                    cached_body=comment.body,
                    creator=user,
                    created=comm["created"],
                    modified=comm["modified"],
                    master_issue=models.IssueLink.objects.get(
                        external_id=comment.notable_iid
                    ),
                    sync_status="sync",
                )
                comm["db_version"] = new_local
            except ObjectDoesNotExist:
                pass  # We couldn't reconcile this to a local user.
        comments_to_return.append(comm)
        ids_to_exclude_from_local.append(lcom.id)
    local_comments = local_comments.exclude(id__in=ids_to_exclude_from_local)
    if local_comments.count() > 0:
        for comment in local_comments:
            comm = {
                "external_id": None,
                "body": comm.cached_body,
                "db_version": comment,
                "creator": comment.creator,
                "created": comment.created,
                "modified": comment.modified,
            }
        comments_to_return.append(comm)
    if not comments_to_return:
        return []
    return sorted(comments_to_return, key=lambda i: i["created"])
