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
    return game.gm == user.gamerprofile


@rules.predicate
def is_public_game(user, game):
    return not game.private


@rules.predicate
def is_scribe(user, game):
    if user.gamerprofile in game.players.all():
        return True
    return False


@rules.predicate
def is_gm_for_game_applied(user, application):
    if user == application.game.gm.user and application.status != 'new':
        return True
    return False


@rules.predicate
def is_game_member(user, game):
    if game.gm.user == user or user.gamerprofile in game.players.all():
        return True
    return False


@rules.predicate
def is_gm(user, game):
    return user.gamerprofile == game.gm


@rules.predicate
def is_not_blocked(user, game):
    if user.gamerprofile.blocked_by(game.gm):
        return False
    return True


game_is_viewable = is_gm | is_not_blocked


@rules.predicate
def is_open_to_players(user, game):
    if game.status in ('open', 'replace'):
        return True
    return False


@rules.predicate
def is_applicant(user, application):
    if user.gamerprofile == application.gamer:
        return True
    return False


@rules.predicate
def is_character_editor(user, character):
    return character.player.gamer.user == user or character.game.gm.user == user


@rules.predicate
def is_character_owner(user, character):
    return character.player.gamer.user == user


is_application_viewer = is_applicant | is_gm_for_game_applied


application_eligible = is_not_blocked & is_open_to_players


can_see_private_game_listing = is_public_game | is_friend | is_same_community_as_game | is_game_member


log_writer = is_game_gm | is_scribe


@rules.predicate
def is_player_owner(user, player):
    return player.gamer.user == user


@rules.predicate
def is_calendar_owner(user, calendar):
    return user.username == calendar.slug


rules.add_perm('game.can_edit_listing', is_game_gm)
rules.add_perm('game.add_character', is_player_owner)
rules.add_perm('game.approve_character', is_game_gm)
rules.add_perm('game.edit_character', is_character_editor)
rules.add_perm('game.view_character', is_game_member)
rules.add_perm('game.delete_character', is_character_owner)
rules.add_perm('game.can_view_listing', game_is_viewable)
rules.add_perm('game.can_apply', application_eligible)
rules.add_perm('game.view_application', is_application_viewer)
rules.add_perm('game.edit_application', is_applicant)
rules.add_perm('game.can_schedule', is_game_gm)
rules.add_perm('game.player_leave', is_player_owner)
rules.add_perm('game.is_member', is_game_member)
rules.add_perm('game.can_view_listing_details', is_game_member)
rules.add_perm('game.edit_create_adventure_log', log_writer)
rules.add_perm('game.delete_adventure_log', is_game_gm)
rules.add_perm('game.can_invite', is_game_gm)
rules.add_perm('game.can_admin_invites', is_game_gm)
rules.add_perm('calendar.can_view', is_calendar_owner)
