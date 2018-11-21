from django.core.cache import cache

from .models import MOTD


def motd(request):
    """
    Try and fetch either the time-based motd, or a random option if none are currently active.
    """
    motd = cache.get_or_set("motd", MOTD.objects.get_motd())
    return {"motd": motd}
