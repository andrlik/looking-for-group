from django.db.models.query_utils import Q
from django.template import Library

from .. import models

register = Library()


@register.simple_tag()
def get_games_for_system(system, active_only=False):
    """
    Returns a queryset of games postings that are directly or indirectly related to a game system
    """
    q_system = Q(game_system=system)
    q_game_edition = Q(published_game__game_system=system)
    q_module = Q(published_module__parent_game_edition__game_system=system)
    queryset = models.GamePosting.objects.filter(q_system | q_game_edition | q_module)
    if active_only:
        queryset = queryset.exclude(status__in=['closed', 'cancel'])
    return queryset


@register.simple_tag()
def get_games_for_edition(edition, active_only=False):
    """
    Returns a queryset of game postings for a given edition
    """
    q_module = Q(published_module__parent_game_edition=edition)
    q_edition = Q(published_game=edition)
    queryset = models.GamePosting.objects.filter(q_module | q_edition)
    if active_only:
        queryset = queryset.exclude(status__in=["closed", "cancel"])
    return queryset


@register.simple_tag()
def get_games_for_published_game(pgame, active_only=False):
    """
    For a given published game, find all the games where it or a descendant
    if in use. Return a queryset.
    """
    q_module = Q(published_module__parent_game_edition__game=pgame)
    q_edition = Q(published_game__game=pgame)
    queryset = models.GamePosting.objects.filter(q_module | q_edition)
    if active_only:
        queryset = queryset.exclude(status__in=['closed', 'cancel'])
    return queryset


@register.simple_tag()
def get_games_for_module(module, active_only=False):
    """
    For a given module return a queryset of related game postings.
    """
    queryset = module.gameposting_set.all()
    if active_only:
        queryset = queryset.exclude(status__in=['closed', 'cancel'])
    return queryset
