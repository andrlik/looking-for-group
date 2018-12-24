from django.template import Library

from .. import models

register = Library()


@register.simple_tag()
def get_modules_for_system(system):
    """
    Return a queryset of modules for a given system.
    """
    return models.PublishedModule.objects.filter(parent_game_edition__id__in=[e.id for e in models.GameEdition.objects.filter(game_system=system)])


@register.simple_tag()
def get_modules_for_pubgame(pubgame):
    """
    Return a queryset of modules for a published game.
    """
    return models.PublishedModule.objects.filter(parent_game_edition__id__in=[e.id for e in models.GameEdition.objects.filter(game=pubgame)])
