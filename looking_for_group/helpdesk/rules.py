import rules


@rules.predicate
def is_user(user, obj=None):
    if user.is_authenticated:
        return True
    return False


@rules.predicate
def is_superuser(user, obj=None):
    if is_user(user) and user.is_superuser:
        return True
    return False


@rules.predicate
def is_issue_creator(user, issuelink):
    if is_user(user) and issuelink.creator == user:
        return True
    return False


@rules.predicate
def is_comment_author(user, commentlink):
    if commentlink and is_user(user) and commentlink.creator == user:
        return True
    return False


@rules.predicate
def is_comment_editable(user, commentlink):
    if commentlink and not commentlink.system_comment:
        return True
    return False


is_comment_editor = is_comment_author | is_superuser

can_edit_comment = is_comment_editor & is_comment_editable

is_issue_editor = is_issue_creator | is_superuser


rules.add_perm("helpdesk.create_issue", is_user)
rules.add_perm("helpdesk.view_issues", is_user)
rules.add_perm("helpdesk.edit_issue", is_issue_editor)
rules.add_perm("helpdesk.add_comment", is_user)
rules.add_perm("helpdesk.edit_comment", can_edit_comment)
rules.add_perm("helpdesk.delete_comment", can_edit_comment)
rules.add_perm("helpdesk.close_issue", is_superuser)
rules.add_perm("helpdesk.delete_issue", is_superuser)
