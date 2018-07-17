import rules
import logging
from django.core.exceptions import ObjectDoesNotExist
from .models import NotInCommunity, BlockedUser


logger = logging.getLogger('rules')


@rules.predicate
def is_user(user, obj=None):
    if user.is_anonymous:
        return False
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
def is_public_community(user, community):
    if community.private:
        return False
    return True


@rules.predicate
def is_not_member(user, community):
    try:
        community.get_role(user.gamerprofile)
    except NotInCommunity:
        return True
    return False


is_joinable = is_user & (is_public_community & is_not_member)


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
    if user.is_anonymous:
        return False
    try:
        community.get_role(user.gamerprofile)
        return True
    except NotInCommunity:
        return False
    return False


def in_same_community_as_gamer(user, gamer):
    communities_to_check = gamer.communities.all()
    logger.debug('found {} communities to check'.format(len(communities_to_check)))
    user_communities = user.gamerprofile.communities.all()
    for community in communities_to_check:
        if community in user_communities:
            logger.debug('One shared community found.')
            return True
    logger.debug('No shared communities found.')
    return False


@rules.predicate
def is_connected_to_gamer(user, gamer):
    logger.debug('Starting check of is {0} connected to gamer {1}.'.format(user.gamerprofile, gamer.user.display_name))
    result = False
    logger.debug('Checking if gamer is private...')
    print(gamer.private)
    if not gamer.private:
        return True
    logger.debug('Gamer is private... moving on.')
    if in_same_community_as_gamer(user, gamer):
        result = True
    # Placeholder for "in same game"
    if user.gamerprofile in gamer.friends.all():
        logger.debug('User is a friend of gamer.')
        result = True
    try:
        BlockedUser.objects.get(blocker=gamer, blockee=user.gamerprofile)
        logger.debug('User is blocked by gamer')
        result = False
    except ObjectDoesNotExist:
        logger.debug('User is not blocked.')
        pass  # Stick with earlier result.
    return result


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
    logger.debug('Checking if {} owns profile {}...'.format(user, gamer))
    return user.gamerprofile == gamer


is_profile_viewer_eligible = is_profile_owner | is_connected_to_gamer

is_profile_viewer = is_user & is_profile_viewer_eligible


@rules.predicate
def is_friend(user, user2):
    if user.gamerprofile in user2.gamerprofile.friends.all():
        return True
    return False


@rules.predicate
def is_note_author(user, note):
    if note.author == user.gamerprofile:
        return True
    return False


rules.add_perm('community.list_communities', is_user)
rules.add_perm('community.view_details', is_community_member | is_public_community)
rules.add_perm('community.edit_community', is_community_admin)
rules.add_perm('community.join', is_joinable)
rules.add_perm('community.leave', is_membership_subject)
rules.add_perm('community.delete_community', is_community_owner)
rules.add_perm('community.kick_user', is_community_admin)
rules.add_perm('community.ban_user', is_community_admin)
rules.add_perm('community.edit_roles', is_community_admin)
rules.add_perm('community.edit_gamer_role', is_community_superior)
rules.add_perm('community.transfer_ownership', is_community_owner)
rules.add_perm('profile.view_detail', is_profile_viewer)
rules.add_perm('profile.edit_profile', is_profile_owner)
rules.add_perm('profile.view_gamer_notes', is_note_author)
