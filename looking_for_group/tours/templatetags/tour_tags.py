import logging

from django.core.exceptions import ObjectDoesNotExist
from django.template import Library

from .. import models

logger = logging.getLogger("tours")

register = Library()


@register.simple_tag()
def get_tour(tour_name):
    tour = None
    try:
        logger.debug("Searching for tour with name {}".format(tour_name))
        tour = (
            models.Tour.objects.prefetch_related("steps")
            .filter(enabled=True)
            .get(name=tour_name)
        )
        logger.debug("Found it!")
    except ObjectDoesNotExist:
        logger.debug("No tour found by that name.")
    return tour


@register.inclusion_tag("tours/tour_rendered.html", takes_context=True)
def render_tour(context, tour):
    logger.debug("Rending html for tour {}".format(tour.name))
    return {
        "tour": tour,
        "completed_tours": context["completed_tours"],
        "user": context["user"],
    }


@register.inclusion_tag("tours/tour_trigger.html", takes_context=True)
def render_tour_trigger(context, tour):
    return {"tour": tour, "user": context["user"]}


@register.simple_tag()
def update_tour_rendered(tour, user):
    logger.debug("Tour completion updated called. Starting checks...")
    tour.users_completed.add(user)
    logger.debug("updated completed tours for user {}".format(user.username))
    return ""
