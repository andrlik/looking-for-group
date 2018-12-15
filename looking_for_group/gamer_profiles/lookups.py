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
    q_list = []
    if gamer.friends.count() > 0:
        friends_q = Q(id__in=[f.id for f in gamer.friends.all()])
        q_list.append(friends_q)
    communities = gamer.communities.all()
    if communities.count() > 0:
        comm_q = None
        for comm in communities:
            if not comm_q:
                comm_q = Q(id__in=[m.gamer.id for m in comm.get_members()])
            else:
                comm_q |= Q(id__in=[m.gamer.id for m in comm.get_members()])
        q_list.append(comm_q)
    if gamer.player_set.count() > 0:
        gm_q = Q(id__in=[p.game.gm.id for p in Player.objects.filter(gamer=gamer).select_related('game', 'game__gm')])
        q_list.append(gm_q)
        fellow_players = Player.objects.select_related("game", "gamer").filter(game__in=[pp.game for pp in Player.objects.filter(gamer=gamer)])
        if fellow_players.count() > 0:
            fellow_player_q = Q(id__in=[p.gamer.id for p in fellow_players])
            q_list.append(fellow_player_q)

    if gamer.gmed_games.count() > 0:
        player_q = Q(id__in=[p.gamer.id for p in Player.objects.select_related('game', 'gamer').filter(game__in=gamer.gmed_games.all())])
        q_list.append(player_q)
    if len(q_list) > 0:
        combine_q = q_list.pop()
        for item in q_list:
            combine_q |= item
        potential_gamer_recipients = models.GamerProfile.objects.select_related('user').filter(combine_q)
        blocks = BlockedUser.objects.select_related('blocker').filter(blockee=gamer)
        if blocks.count() > 0:
            potential_gamer_recipients = potential_gamer_recipients.exclude(Q(id__in=blocks))
        if potential_gamer_recipients.count() > 0:
            return User.objects.filter(id__in=[g.user.id for g in potential_gamer_recipients])
    return []


@register('gamers')
class GamerLookup(LookupChannel):

    model = models.GamerProfile

    def get_query(self, q, request):
        potential_recipients = get_users_available_for_messaging(request.user.gamerprofile)
        username_q = Q(username__icontains=q)
        display_name_q = Q(display_name__icontains=q)
        return potential_recipients.filter(username_q | display_name_q)
