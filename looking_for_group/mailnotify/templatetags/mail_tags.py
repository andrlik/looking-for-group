from django.template import Library
from django.utils import timezone

register = Library()


@register.simple_tag()
def get_silence_end(user):
    """
    For a given user, return when their silence ends.

    :returns: None if not silenced, an end date, or the string "eternity"
    """
    if user.silence_terms.filter(ending__isnull=True).count() > 0:
        return "eternity"
    active_silences = user.silence_terms.filter(ending__gte=timezone.now())
    if active_silences.count() > 0:
        return active_silences.latest('ending')
    return None


@register.simple_tag()
def get_recipient_string(gamer_list):
    """
    For a list or queryset of gamers, return the postman formatted recipient string.

    :returns: a string of usernames in postman syntax uname:uname:uname
    """
    usernames = [g.username for g in gamer_list]
    return ":".join(usernames)
