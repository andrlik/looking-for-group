from markdown import markdown
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from . import models
from ..users.models import User


@receiver(pre_save, sender=models.GamerCommunity)
def generate_rendered_html_from_description(sender, instance, *args, **kwargs):
    """
    Parse the description with markdown and save the result.
    """
    instance.description_rendered = markdown(instance.description)


@receiver(pre_save, sender=models.GamerNote)
def generate_rendered_note_body(sender, instance, *args, **kwargs):
    """
    Parse and convert markdown to rendered body.
    """
    instance.body_rendered = markdown(instance.body)


@receiver(post_save, sender=User)
def generate_default_gamer_profile(sender, instance, created, *args, **kwargs):
    """
    If a new user is created, generate an automatic gamer profile.
    """
    if created:
        models.GamerProfile.objects.get_or_create(user=instance)
