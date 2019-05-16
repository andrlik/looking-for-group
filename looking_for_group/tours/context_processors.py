from django.core.cache import cache


def completed_tours(request):
    """
    If a user is authenticated, try to fetch their current completed tours from the cache.
    NOTE: This means that when changing this value we need to remember to explicitly increment the cache version
    for the key [username]_completed_tours
    """
    completed_tours = None
    if request.user.is_authenticated:
        completed_tours = cache.get_or_set("{}_completed_tours".format(request.user.username), request.user.completed_tours.all())
    return {"completed_tours": completed_tours}
