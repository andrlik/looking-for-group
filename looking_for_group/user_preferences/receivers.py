from django.db.models.signals import post_save
from django.dispatch import receiver

from ..gamer_profiles.models import GamerProfile
from .models import Preferences


@receiver(post_save, sender=GamerProfile)
def create_initial_settings(sender, instance, created, *args, **kwargs):
    if created:
        Preferences.objects.create(gamer=instance)
