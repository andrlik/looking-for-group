from django.template import Library
from django.utils.html import format_html
from .. import models

register = Library()


@register.simple_tag(takes_context=True)
def community_role_flag(context, community):
    '''
    Takes an instance of community and returns the current user's role
    in it as an HTML span, if applicable.
    '''
    if not isinstance(community, models.GamerCommunity) or not context['request'].user.is_authenticated:
        return None
    try:
        role = community.get_role(context['request'].user.gamerprofile)
    except models.NotInCommunity:
        return None
    return format_html("<span class='membership'>{}</span>", role)
