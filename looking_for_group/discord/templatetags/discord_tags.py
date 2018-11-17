from django.core.exceptions import ObjectDoesNotExist
from django.template import Library

from .. import models

register = Library()


@register.simple_tag()
def gamer_discord_link(user):
    """
    For a given user record, return the gamer discord link if any.
    """
    if user.is_authenticated:
        try:
            gdl = models.GamerDiscordLink.objects.get(gamer=user.gamerprofile)
            return gdl
        except ObjectDoesNotExist:
            pass  # We'll return None anyway
    return None


@register.simple_tag()
def community_discord_link(community):
    """
    For a given community, return it's discord link object if it exists.
    """
    if community.linked_with_discord:
        try:
            cdl = models.CommunityDiscordLink.objects.get(community=community)
            return cdl
        except ObjectDoesNotExist:
            pass  # We'll return None anyway
    return None
