from django import template
from django.contrib.contenttypes.models import ContentType

from ..models import GameLibrary

register = template.Library()


@register.simple_tag
def is_in_collection(obj, gamer):
    """
    For a given object and gamer, check to see if it exists in their game library.

    :retuns either the collected copy object or none
    """
    library, created = GameLibrary.objects.get_or_create(user=gamer.user)
    if not created:
        copy_count = obj.collected_copies.filter(library=library)
        if copy_count:
            return copy_count[0]
    return None


@register.simple_tag
def get_content_type(obj):
    ct = ContentType.objects.get_for_model(obj)
    return ct
