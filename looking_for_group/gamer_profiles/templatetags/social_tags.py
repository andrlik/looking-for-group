from django.template import Library
from django.urls import reverse
from django.utils.html import format_html

from .. import models

register = Library()


@register.simple_tag(takes_context=True)
def community_role_flag(context, community):
    """
    Takes an instance of community and returns the current user's role
    in it as an HTML span, if applicable.
    """
    if (
        not isinstance(community, models.GamerCommunity)
        or not context["request"].user.is_authenticated
    ):
        return ""
    try:
        role = community.get_role(context["request"].user.gamerprofile)
    except models.NotInCommunity:
        role = None
    if role:
        extra_class = "secondary"
        if role == "Admin":
            extra_class = "primary"
        return format_html("<span class='membership label {}'>{}</span>", extra_class, role)
    else:
        if community.private:
            return format_html(
                "<a href='{}' class='button'>Apply</a>",
                reverse(
                    "gamer_profiles:community-apply", kwargs={"community": community.pk}
                ),
            )
        else:
            return format_html(
                "<a href='{}' class='button'>Join</a>",
                reverse(
                    "gamer_profiles:community-join", kwargs={"community": community.pk}
                ),
            )
