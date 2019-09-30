import logging
from datetime import datetime

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from pytz import timezone as ptimezone

from ..users.models import User
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


def is_system_comment(comment):
    if comment.system or comment.body.strip() in [
        "reopened",
        "closed",
        "changed the description",
        "changed the title",
    ]:
        return True
    return False


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
    logger.debug("Starting comment reconciliation...")
    remote_comments = issuelink.get_external_comments()
    logger.debug("Fetched {} remote comments...".format(len(remote_comments)))
    local_comments = issuelink.comments.all()
    logger.debug("Fetched {} local comments...".format(local_comments.count()))
    local_comment_ids = [c.external_id for c in local_comments]
    if not remote_comments:
        logger.debug("No remote comments so only returning local comments.")
        return local_comments
    comments_to_return = []
    ids_to_exclude_from_local = []
    for comment in remote_comments:
        logger.debug("Begging check for remote comment {}".format(comment.id))
        if comment.body and comment.body != "":
            comm = {
                "external_id": comment.id,
                "body": comment.body,
                "db_version": None,
                "creator": comment.author["username"],
                "created": datetime.strptime(
                    comment.created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=ptimezone("UTC")),
                "modified": datetime.strptime(
                    comment.updated_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=ptimezone("UTC")),
                "gl_version": comment,
            }
            if comm["body"] == "reopened":
                comm["body"] = "Reopened this issue."
            if comm["body"] == "closed":
                comm["body"] = "Closed this issue."
            if "email" in comment.author.keys():
                logger.debug("Received an email and adding it to object.")
                comm["creator_email"] = comment.author["email"]
            else:
                if (
                    "username" in comment.author.keys()
                    and comment.author["username"]
                    == settings.GITLAB_DEFAULT_REMOTE_USERNAME
                ):
                    logger.debug("Found a gitlab username, and it's mine!")
                    try:
                        email = EmailAddress.objects.get(
                            user=User.objects.get(
                                username=settings.GITLAB_DEFAULT_USERNAME
                            ),
                            primary=True,
                        ).email
                        comm["creator_email"] = email
                        logger.debug("Setting email address to {}".format(email))
                    except ObjectDoesNotExist:
                        logger.debug("Couldn't find the primary account. Skipping...")
                        pass
            if str(comment.id) in local_comment_ids:
                logger.debug(
                    "This comment id can be found in our local comments. Retrieving local details..."
                )
                lcom = local_comments.get(external_id=str(comment.id))
                comm["db_version"] = lcom
                comm["creator"] = lcom.creator
                comm["body"] = lcom.cached_body
                logger.debug(
                    "Adding info to exlude this local id of {} matching external id of {} from append...".format(
                        lcom.id, comment.id
                    )
                )
                ids_to_exclude_from_local.append(lcom.id)
            if (
                not comm["db_version"]
                and use_emails
                and ("email" in comment.author.keys() or "creator_email" in comm.keys())
            ):
                # TODO: Try and reconcile against a user via email address.
                logger.debug(
                    "This comment doesn't have a local equivelent, but we did receive an email. Trying to reconcile with an existing user..."
                )
                try:
                    if "creator_email" in comm.keys():
                        user = EmailAddress.objects.get(
                            email=comm["creator_email"]
                        ).user
                    else:
                        user = EmailAddress.objects.get(
                            email=comment.author["email"]
                        ).user
                    logger.debug("Found matching user of {}".format(user.username))
                    comm["creator"] = user
                    logger.debug("Creating local copy...")
                    lcom = models.IssueCommentLink.objects.create(
                        external_id=comment.id,
                        cached_body=comment.body,
                        creator=user,
                        created=comm["created"],
                        modified=comm["modified"],
                        master_issue=issuelink,
                        sync_status="sync",
                    )
                    if is_system_comment(comment):
                        lcom.system_comment = True
                        lcom.save()
                    comm["db_version"] = lcom
                    logger.debug(
                        "Successfully created local copy with id of {} for external comment of {}. Excluding from append.".format(
                            lcom.id, comment.id
                        )
                    )
                    ids_to_exclude_from_local.append(lcom.id)
                except ObjectDoesNotExist:
                    logger.debug(
                        "We couldn't' find a matching email address, so proceeding without a local match."
                    )
                    pass  # We couldn't reconcile this to a local user.
            logger.debug("Adding this reconciled comment to return list.")
            comments_to_return.append(comm)
    local_comments = local_comments.exclude(id__in=ids_to_exclude_from_local)
    if local_comments.count() > 0:
        logger.debug(
            "There are {} additional local comments to pull in...".format(
                local_comments.count()
            )
        )
        for comment in local_comments:
            comm = {
                "external_id": None,
                "body": comment.cached_body,
                "db_version": comment,
                "creator": comment.creator,
                "created": comment.created,
                "modified": comment.modified,
            }
        logger.debug("Appending local comment with id {}".format(comment.id))
        comments_to_return.append(comm)
    if not comments_to_return:
        logger.debug("No comments to return.")
        return []
    logger.debug("Returning sorted comment list.")
    return sorted(comments_to_return, key=lambda i: i["created"])


def get_default_actor_for_syncs():  # pragma: no cover
    return get_user_model().objects.get(username=settings.GITLAB_DEFAULT_USERNAME)
