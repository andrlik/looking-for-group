from django.db.models.signals import pre_save
from django.dispatch import receiver
from markdown import markdown

from . import models


@receiver(pre_save, sender=models.Step)
def process_markdown_description(sender, instance, *args, **kwargs):
    """
    Save the rendered markdown to the correct description.
    """
    instance.guide_text_rendered = markdown(instance.guide_text)
