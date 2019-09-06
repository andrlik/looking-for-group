import logging

import gitlab

from .base import AuthenticationError, HelpDeskConnector, OperationError

logger = logging.getLogger("helpdesk")


class GitlabConnector(HelpDeskConnector):
    """
    Github implementation of our base connector.
    """

    project = None

    def __init__(self, gitlab_url, personal_token, project, *args, **kwargs):
        """
        Initiates a Gitlab api instance, authenticates it and sets it as our authenticated
        client. If project is specified, it populates the attribute.

        :param gitlab_url: Url of the gitlab instance
        :param personal_token: Personal token of the user that will be used to connect.
        :param project: Project name
        :type gitlab_url: string
        :type personal_token: string
        :type project: string
        """
        try:
            self.authenticated_client = self.get_authenticated_client(
                gitlab_url, personal_token
            )
        except gitlab.exceptions.GitlabAuthenticationError as gae:  # pragma: no cover
            raise AuthenticationError(str(gae))

        try:
            self.project = self.authenticated_client.projects.get(project, lazy=True)
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(
                "You have to specify a project, and your supplied project id/namespace failed with error: {}".format(
                    str(goe)
                )
            )

    def get_authenticated_client(self, gitlab_url, personal_token, *args, **kwargs):
        """
        Create the authenticated client and return it.

        :param gitlab_url: URL to the gitlab instance
        :param personal_token: Private token for the user connecting.
        :type gitlab_url: string
        :type pesonal_token: string
        :return: An authencticated instance of the gitlab api client
        :rtype: :class:`gitlab.Gitlab`
        """
        return gitlab.Gitlab(url=gitlab_url, private_token=personal_token)

    def get_issues(
        self,
        issue_id_list=None,
        include_confidential=False,
        filter_status="opened",
        *args,
        **kwargs
    ):
        """
        Retrieve a list of issues based on the supplied list or all available issues.

        :param issue_id_list: A list of issue ids to retrieve
        :param include_confidential: Whether to include the confidential issues. Defaults to False
        :param filter_status: What status to use when filtering the data. Optional.
        :type issue_id_list: Python list
        :type include_confidental: bool
        :type filter_status: string
        :return: Matching issues
        :rtype: list of :class:`gitlab.v4.objects.ProjectIssue` objects
        """
        objects_to_return = []
        try:
            if issue_id_list:
                issues = self.project.issues.list(
                    iids=issue_id_list, state=filter_status, all=True
                )
            else:
                issues = self.project.issues.list(state=filter_status, all=True)
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        if not include_confidential:
            for x in issues:
                if not x.confidential:
                    objects_to_return.append(x)
        else:
            objects_to_return = issues
        return objects_to_return

    def get_issue(self, issue_id, lazy=False, *args, **kwargs):
        """
        Retrieve the issue for a given id

        :param issue_id: ID of the issue in question.
        :type issue_id: int
        :return: Issue object
        :rtype: :class:`gitlab.v4.objects.ProjectIssue`
        """
        try:
            issue = self.project.issues.get(issue_id, lazy=lazy)
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return issue

    def create_issue(self, title, description, *args, **kwargs):
        """
        Create an issue and return the issue.

        :param title: Title of the issue to create
        :param description: Description of the issue to create. (Markdown formatting can be used.)
        :type title: string
        :type description: string
        :returns: The created issue as a python object.
        :rtype: :class:`gitlab.v4.objects.ProjectIssue`
        """
        try:
            issue = self.project.issues.create(
                {"title": title, "description": description}
            )
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return issue

    def edit_issue(self, issue, title, description, *args, **kwargs):
        """
        Edit an existing issue.

        :param issue: The issue to be updated
        :param title: The new title
        :param description: The new description
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :type title: string
        :type description: string
        :return: Updated issue object
        :rtype: :class:`gitlab.v4.objects.ProjectIssue`
        """
        try:
            issue.title = title
            issue.description = description
            issue.save()
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return issue

    def reopen_issue(self, issue, *args, **kwargs):
        """
        Reopen a given issue.

        :param issue: The issue to reopen.
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :return: The updated issue
        :rtype: :class:`gitlab.v4.objects.ProjectIssue`
        """
        try:
            issue.state_event = "reopen"
            issue.save()
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return issue

    def close_issue(self, issue, comment_text=None, *args, **kwargs):
        """
        Close a given issue.

        :param issue: The issue to close
        :param comment_text: Optional comment to include when closing.
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :type comment_text: string or None
        :return: Updated issue object, note object or none
        :rtype: :class:`gitlab.v4.objects.ProjectIssue`, :class:`gitlab.v4.objects.ProjectIssueNote` or None
        """
        note = None
        try:
            if comment_text:
                logger.debug(
                    "Close issue was also sent with a comment. Creating comment with body '{}'".format(
                        comment_text
                    )
                )
                note = issue.notes.create({"body": comment_text})
                if note and hasattr(note, "id"):
                    logger.debug(
                        "Succesfully created the comment to use in closing the issue. Comment id is {}".format(
                            note.id
                        )
                    )
            issue.state_event = "close"
            issue.save()
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return issue, note

    def get_issue_comments(self, issue, *args, **kwargs):
        """
        Get the comments for a specific issue.

        :param issue: The issue in question
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :return: A list of :class:`gitlab.v4.objects.ProjectIssueNote`
        :rtype: list
        """
        try:
            comment_list = issue.notes.list(all=True)
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return comment_list

    def get_issue_comment(self, issue, comment_id, lazy=False, *args, **kwargs):
        """
        Get a single comment from a given issue.

        :param issue: The issue the comment belongs to.
        :param comment_id: The id of the comment to query.
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :type comment_id: string
        :return: The comment object
        :rtype: :class:`gitlab.v4.objects.ProjectIssueNote`
        """
        try:
            comment = issue.notes.get(comment_id, lazy=lazy)
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return comment

    def comment_on_issue(self, issue, comment_text, *args, **kwargs):
        """
        Add a comment to the issue.

        :param issue: The issue to add a comment to.
        :comment_text: The text of the comment to add.
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :return: The note that was added.
        :rtype: :class:`gitlab.v4.objects.ProjectIssueNote`
        """
        try:
            note = issue.notes.create({"body": comment_text})
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return note

    def edit_comment(self, comment, comment_text, *args, **kwargs):
        """
        Update the comment on an issue.

        :param comment: The note to delete.
        :param comment_text: The new comment body
        :type comment: :class:`gitlab.v4.objects.ProjectIssueNote`
        :type comment_text: string
        :return: The updated note object.
        :rtype: :class:`gitlab.v4.objects.ProjectIssueNote`
        """
        try:
            comment.body = comment_text
            comment.save()
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
        return comment

    def delete_comment(self, comment, *args, **kwargs):
        """
        Delete a commen on an issue.

        :param comment: The note to delete.
        :type comment: :class:`gitlab.v4.objects.ProjectIssueNote`
        """
        try:
            comment.delete()
        except gitlab.exceptions.GitlabOperationError as goe:  # pragma: no cover
            raise OperationError(str(goe))
