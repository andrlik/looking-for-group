from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def google_maps_api():
    return settings.GOOGLE_MAPS_API_KEY
