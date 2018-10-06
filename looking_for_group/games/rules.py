import rules

from ..gamer_profiles.rules import is_community_member, is_friend


@rules.predicate
def is_same_community_as_game(user, game):
    for community in game.communities:
        if is_community_member(user, community):
            return True
    return False


@rules.predicate
def is_game_gm(user, game):
    if user.gamerprofile in game.gm.all():
        return True
    return False


@rules.predicate
def is_public_game(user, game):
    return not game.private


@rules.predicate
def is_scribe(user, game):
    if user.gamerprofile in game.players.all():
        return True
    return False


@rules.predicate
def is_game_member(user, game):
    if user.gamerprofile in game.players.all() or user.gamerprofile == game.gm:
        return True
    return False


can_see_private_game_listing = is_public_game | is_friend | is_same_community_as_game | is_game_member


log_writer = is_game_gm | is_scribe


@rules.predicate
def is_calendar_owner(user, calendar):
    return user.username == calendar.slug


rules.add_perm('game.edit_listing', is_game_gm)
rules.add_perm('game.can_view_listing_summary', can_see_private_game_listing)
rules.add_perm('game.can_schedule', is_game_gm)
rules.add_perm('game.is_member', is_game_member)
rules.add_perm('game.can_view_listing_details', is_game_member)
rules.add_perm('game.edit_create_adventure_log', log_writer)
rules.add_perm('game.delete_adventure_log', is_game_gm)
rules.add_perm('calendar.can_view', is_calendar_owner)
