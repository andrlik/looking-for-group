from ajax_select import LookupChannel, register
from django.db.models.query_utils import Q

from . import models
from ..gamer_profiles.models import BlockedUser
from ..games.models import Player
from ..users.models import User


def get_users_available_for_messaging(gamer):
    """
    For a given gamer, lookup users for whom they are allowed to message.
    """
    friends_q = Q(id__in=[f.id for f in gamer.friends.all()])
    communities = gamer.communities.all()
    comm_q = None
    for comm in communities:
        if not comm_q:
            comm_q = Q(id__in=[m.gamer.id for m in comm.get_members()])
        else:
            comm_q |= Q(id__in=[m.gamer.id for m in comm.get_members()])
    gm_q = Q(id__in=[p.game.gm.id for p in Player.objects.filter(gamer=gamer).select_related('game', 'game__gm')])
    player_q = Q(id__in=[p.gamer.id for p in Player.objects.select_related('game', 'gamer').filter(game__in=gamer.gmed_games.all())])
    block_q = Q(id__in=[b.blocker.id for b in BlockedUser.objects.select_related('blocker').filter(blockee=gamer)])
    potential_gamer_recipients = models.GamerProfile.objects.select_related('user').filter(friends_q | comm_q | gm_q | player_q).exclude(block_q)
    return User.objects.filter(id__in=[g.user.id for g in potential_gamer_recipients])


@register('gamers')
class GamerLookup(LookupChannel):

    model = models.GamerProfile

    def get_query(self, q, request):
        potential_recipients = get_users_available_for_messaging(request.user.gamerprofile)
        username_q = Q(username__icontains=q)
        display_name_q = Q(display_name__icontains=q)
        return potential_recipients.filter(username_q | display_name_q)
