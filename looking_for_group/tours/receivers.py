from django.core.cache import cache
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from . import models


@receiver(m2m_changed, sender=models.Tour.users_completed.through)
def update_cache_of_completed_tours(sender, instance, action, reverse, model, pk_set, *args, **kwargs):
    """
    Whenever the completed tours of a user are changed, invalidate the caches.
    """
    if action in ["post_add", "post_remove"]:
        if reverse:
            cache.set("{}_completed_tours".format(instance.username), models.Tour.objects.filter(id__in=pk_set))
        else:
            for user in model.objects.filter(id__in=pk_set):
                cache.set("{}_completed_tours".format(user.username), user.completed_tours.all())
