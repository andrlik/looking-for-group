import logging

from django.conf import settings

from .backends import AuthenticationError, GitlabConnector, NotImplementedError
from .models import IssueLink

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
    except AuthenticationError as ae:
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
    if not backend_client:
        backend_client = get_backend_client()
    return IssueLink.objects.create(
        external_id=remote_issue.iid,
        creator=creator,
        cached_status=remote_issue.state,
        cached_title=remote_issue.title,
        cached_description=remote_issue.description,
        cached_comment_count=remote_issue.user_notes_count,
        external_url=remote_issue.web_url,
        sync_status="sync",
    )
