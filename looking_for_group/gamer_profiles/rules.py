import rules
from django.core.exceptions import ObjectDoesNotExist
from .models import NotInCommunity, BlockedUser


@rules.predicate
def is_user(user):
    return True


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
def is_membership_subject(user, membership):
    if membership.gamer == user.gamerprofile:
        return True
    return False


@rules.predicate
def is_community_owner(user, community):
    if user.gamerprofile == community.owner:
        return True
    return False


is_community_superior = is_community_owner | is_community_admin


@rules.predicate
def is_community_member(user, community):
    try:
        user.gamerprofile.get_role(community)
        return True
    except NotInCommunity:
        return False


def in_same_community_as_gamer(user, gamer):
    communities_to_check = gamer.communities.all()
    user_communities = user.gamerprofile.communities.all()
    for community in communities_to_check:
        if community in user_communities:
            return True
    return False


@rules.predicate
def is_connected_to_gamer(user, gamer):
    if not gamer.private:
        return True
    if in_same_community_as_gamer(user, gamer):
        return True
    # Placeholder for "in same game"
    # placeholder for friends
    try:
        BlockedUser.objects.get(blocker=gamer, blockee=user.gamerprofile)
    except ObjectDoesNotExist:
        return True
    return False


@rules.predicate
def is_blocker(user, block_file):
    if block_file.blocker == user.gamerprofile:
        return True
    return False


@rules.predicate
def is_muter(user, mute_file):
    if mute_file.muter == user.gamerprofile:
        return True
    return False


@rules.predicate
def is_profile_owner(user, gamer):
    return gamer.user == user


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

rules.add_perm('community.list_communities', is_user)
rules.add_perm('community.view_details', is_community_member)
rules.add_perm('community.edit_community', is_community_admin)
rules.add_perm('community.leave', is_membership_subject)
rules.add_perm('community.delete_community', is_community_owner)
rules.add_perm('community.kick_user', is_community_admin)
rules.add_perm('community.ban_user', is_community_admin)
rules.add_perm('community.edit_roles', is_community_admin)
rules.add_perm('community.edit_gamer_role', is_community_superior)
rules.add_perm('community.transfer_ownership', is_community_owner)
rules.add_perm('profile.view_detail', is_connected_to_gamer)
rules.add_perm('profile.edit_profile', is_profile_owner)
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
