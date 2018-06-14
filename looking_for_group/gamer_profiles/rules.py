import rules
from .models import NotInCommunity


@rules.predicate
def is_community_admin(user, community):
    try:
        role = user.gamerprofile.get_role(community)
    except NotInCommunity:
        return False
    if role == 'Admin':
        return True
    return False


@rules.predicate
def is_community_member(user, community):
    try:
        user.gamerprofile.get_role(community)
        return True
    except NotInCommunity:
        return False


@rules.predicate
def is_same_community_as_game(user, game):
    for community in game.communities:
        if is_community_member(user, community):
            return True
    return False


@rules.predicate
def is_friend(user, user2):
    if user.gamerprofile in user2.gamerprofile.friends.all():
        return True
    return False


can_see_private_game_listing = is_friend | is_same_community_as_game


@rules.predicate
def is_game_gm(user, game):
    if user.gamerprofile in game.gm.all():
        return True
    return False


@rules.predicate
def is_scribe(user, game):
    if user.gamerprofile in game.scribes.all():
        return True
    return False


@rules.predicate
def is_note_author(user, note):
    if note.author == user.gamerprofile:
        return True
    return False


@rules.predicate
def is_game_member(user, game):
    if user.gamerprofile in game.players.all() or user.gamerprofile == game.gm:
        return True
    return False


log_writer = is_game_gm | is_scribe

rules.add_perm('community.kick_user', is_community_admin)
rules.add_perm('community.ban_user', is_community_admin)
rules.add_perm('game.edit_players', is_game_gm)
rules.add_perm('game.attendance', is_game_gm)
rules.add_perm('game.close_game', is_game_gm)
rules.add_perm('game.cancel_game', is_game_gm)
rules.add_perm('game.view_game_details', is_game_member)
rules.add_perm('game.edit_create_adventure_log', log_writer)
rules.add_perm('game.delete_adventure_log', is_game_gm)
rules.add_perm('game.view_game_listing_detail', can_see_private_game_listing)
rules.add_perm('game.post_game_to_community', is_community_member)
rules.add_perm('game.view_gamer_notes', is_note_author)
