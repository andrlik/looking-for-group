from django.core.exceptions import ObjectDoesNotExist
from django.template import Library

from .. import models

register = Library()


@register.inclusion_tag("tours/tour_rendered.html", takes_context=True)
def render_tour(context, tour_name):
    tour = None
    try:
        tour = models.Tour.objects.prefetch_related('steps').get(name=tour_name)
    except ObjectDoesNotExist:
        pass
    return {"tour": tour}


@register.inclusion_tag("tours/tour_trigger.html", takes_context=True)
def render_trigger(context, tour_name):
    tour = None
    try:
        tour = models.Tour.objects.get(name=tour_name)
    except ObjectDoesNotExist:
        pass
    return {"tour": tour}


@register.simple_tag()
def update_rendered(tour, user):
    tour.users_completed.add(user)
