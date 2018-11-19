from django.dispatch import receiver
from django.db.models.signals import pre_save
from markdown import markdown

from . import models


@receiver(pre_save, sender=models.PublishedGame)
@receiver(pre_save, sender=models.GameEdition)
@receiver(pre_save, sender=models.GameSystem)
def render_markdown_body(sender, instance, *args, **kwargs):
    if instance.description:
        instance.description_rendered = markdown(instance.description)
    else:
        instance.description_rendered = None
