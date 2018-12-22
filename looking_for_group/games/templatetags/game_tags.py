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
