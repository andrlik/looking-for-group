class HelpDeskAPIBackendError(Exception):
    pass


class NotImplementedError(HelpDeskAPIBackendError):
    pass


class AuthenticationError(HelpDeskAPIBackendError):
    pass


class OperationError(HelpDeskAPIBackendError):
    pass


class HelpDeskConnector(object):
    """
    A base connector object. None of the methods below are implemented as it will vary for each backend.
    NOTE: Permissions logic should exist in your app, not within the connector itself. The job of the connector
    is only to provide you with a consistent API for various backends.
    """

    authenticated_client = None

    def __init__(self, *args, **kwargs):
        pass

    def get_authenticated_client(self, *args, **kwargs):
        """
        Create an authenticated api client and associate it with
        self.authenticated_client
        """
        raise NotImplementedError

    def get_issues(self, issue_id_list=None, *args, **kwargs):
        """
        Retrieve issue data for a specified set of issues, or retrieve all public facing issues.
        """
        raise NotImplementedError

    def get_issue(self, issue_id, *args, **kwargs):
        """
        Retrieve issue information from the backend.
        """
        raise NotImplementedError

    def create_issue(self, title, description, *args, **kwargs):
        """
        Create an issue and associate it with the user.
        """
        raise NotImplementedError

    def edit_issue(self, issue, title, description, *args, **kwargs):
        """
        Edit the issue. Only the creator or admin should be able to do this.
        """
        raise NotImplementedError

    def get_issue_comments(self, issue, *args, **kwargs):
        """
        Get all the comments on an issue in chronological order.
        """
        raise NotImplementedError

    def get_issue_comment(self, issue, comment_id):
        """
        Get the details for a given note for a specific issue.
        """
        raise NotImplementedError

    def comment_on_issue(self, issue, comment_text, *args, **kwargs):
        """
        Add a comment to an issue from the user.
        """
        raise NotImplementedError

    def edit_comment(self, comment, new_comment_text, *args, **kwargs):
        """
        Allow a user to edit their own comment.
        """
        raise NotImplementedError

    def delete_comment(self, comment, *args, **kwargs):
        """
        Allow a user to delete their own comment.
        """
        raise NotImplementedError

    def close_issue(self, issue, comment_text=None, *args, **kwargs):
        """
        Close an issue.
        """
        raise NotImplementedError

    def reopen_issue(self, issue, *args, **kwargs):
        """
        Reopen an issue
        """
        raise NotImplementedError
