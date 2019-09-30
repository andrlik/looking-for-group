from avatar.templatetags.avatar_tags import avatar as avatar_tag
from django.contrib.auth import get_user_model
from django.template import Library
from django.template.defaultfilters import safe
from django.urls import reverse

register = Library()


@register.simple_tag
def get_url_from_listmode(listmode, page=None):
    """
    Get the url to use in pagination elements.

    :param listmode: The listmode value that was provided to the context.
    :param page: The page number to use if any in the url.
    :type listmode: string
    :type page: int
    :return: The url to use.
    :rtype: string
    """
    if "my" in listmode:
        url = reverse("helpdesk:my-issue-list")
    else:
        url = reverse("helpdesk:issue-list")
    if "close" in listmode or page:
        url = base_url + "?"
        variable_count = 0
        if "close" in listmode:
            url = url + "status=closed"
            variable_count += 1
        if page:
            if variable_count > 0:
                url = url + "&"
            url = url + "page={}".format(page)
    return url


@register.simple_tag
def render_commenter_id(reconciled_comment):
    """
    For given reconciled comment, resolve whether the author is an internal user or an external account.

    :param reconciled_comment: The comment to evaluate.
    :type reconciled_comment: dict

    :return: The html to display
    :rtype: string
    """
    creator_str = ""
    avatar_val = avatar_tag(
        reconciled_comment["creator"], size=30, **{"class": "avatar"}
    )
    if isinstance(reconciled_comment["creator"], get_user_model()):
        avatar_val = avatar_tag(
            reconciled_comment["creator"], size=30, **{"class": "avatar"}
        )
        creator_str = '<a href="{}">{} {}</a>'.format(
            reconciled_comment["creator"].gamerprofile.get_absolute_url(),
            avatar_val,
            reconciled_comment["creator"].gamerprofile,
        )
    else:
        avatar_val = avatar_tag("nobody", size=30, **{"class": "avatar"})
        if (
            "creator_email" in reconciled_comment.keys()
            and reconciled_comment["creator_email"]
        ):
            avatar_val = avatar_tag(
                reconciled_comment["creator_email"], size=30, **{"class": "avatar"}
            )
        creator_str = "{} {} (Remote)".format(
            avatar_val, reconciled_comment["gl_version"].author["name"]
        )
    return safe(creator_str)
