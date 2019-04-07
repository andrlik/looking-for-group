from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver
from django_q.tasks import async_task
from ..gamer_profiles.models import GamerProfile
from . import models
from .tasks import recalc_library_content


@receiver(post_save, sender=models.Book)
@receiver(post_delete, sender=models.Book)
def queue_calc_updates(sender, instance, *args, **kwargs):
    """
    When a book is created or edited, queue up the task to update the denormalized library fields.
    """
    async_task(recalc_library_content, instance.library)


@receiver(post_save, sender=GamerProfile)
def create_empty_library_for_user(sender, instance, created, *args, **kwargs):
    if created:
        models.GameLibrary.objects.create(user=instance.user)
