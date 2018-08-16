import rules
from rules import predicate
import logging
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import NotInCommunity, BlockedUser, BannedUser, KickedUser


logger = logging.getLogger("rules")


@predicate
def is_user(user, obj=None):  # noqa
    if user.is_anonymous:
        return False
    return True


@predicate
def is_community_admin(user, community):
    try:
        role = user.gamerprofile.get_role(community)
    except NotInCommunity:
        return False
    if role == "Admin":
        return True
    return False


@predicate
def is_public_community(user, community):  # noqa
    if community.private:
        return False
    return True


@predicate
def is_not_member(user, community):
    try:
        community.get_role(user.gamerprofile)
    except NotInCommunity:
        return True
    return False


is_joinable = is_user & (is_public_community & is_not_member)


@predicate
def is_membership_subject(user, membership):
    if membership.gamer == user.gamerprofile:
        return True
    return False


@predicate
def is_community_owner(user, community):
    if user.gamerprofile == community.owner:
        return True
    return False


is_community_superior = is_community_owner | is_community_admin


@predicate
def is_not_comm_blocked(user, community):
    bans = BannedUser.objects.filter(banned_user=user.gamerprofile, community=community)
    if bans:
        return False
    kicks = KickedUser.objects.filter(
        kicked_user=user.gamerprofile, community=community, end_date__gt=timezone.now()
    )
    if kicks:
        return False
    return True


@predicate
def is_applicant(user, application):
    return application.gamer == user.gamerprofile


is_eligible_applicant = is_user & (is_not_member & is_not_comm_blocked)


@predicate
def is_application_approver(user, application):
    if application.status == "new":
        return False
    return is_community_superior(user, application.community)


@predicate
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
    logger.debug("found {} communities to check".format(len(communities_to_check)))
    user_communities = user.gamerprofile.communities.all()
    for community in communities_to_check:
        if community in user_communities:
            logger.debug("One shared community found.")
            return True
    logger.debug("No shared communities found.")
    return False


@predicate
def is_connected_to_gamer(user, gamer):
    logger.debug(
        "Starting check of is {0} connected to gamer {1}.".format(
            user.gamerprofile, gamer.user.display_name
        )
    )
    result = False
    logger.debug("Checking if gamer is private...")
    print(gamer.private)
    if not gamer.private:
        return True
    logger.debug("Gamer is private... moving on.")
    if in_same_community_as_gamer(user, gamer):
        result = True
    # Placeholder for "in same game"
    if user.gamerprofile in gamer.friends.all():
        logger.debug("User is a friend of gamer.")
        result = True
    try:
        BlockedUser.objects.get(blocker=gamer, blockee=user.gamerprofile)
        logger.debug("User is blocked by gamer")
        result = False
    except ObjectDoesNotExist:
        logger.debug("User is not blocked.")
        pass  # Stick with earlier result.
    return result


@predicate
def is_blocker(user, block_file):
    if block_file.blocker == user.gamerprofile:
        return True
    return False


@predicate
def is_muter(user, mute_file):
    if mute_file.muter == user.gamerprofile:
        return True
    return False


@predicate
def is_profile_owner(user, gamer):
    logger.debug("Checking if {} owns profile {}...".format(user, gamer))
    return user.gamerprofile == gamer


is_profile_viewer_eligible = is_profile_owner | is_connected_to_gamer

is_profile_viewer = is_user & is_profile_viewer_eligible


@predicate
def is_friend(user, user2):
    if user.gamerprofile in user2.gamerprofile.friends.all():
        return True
    return False


@predicate
def is_possible_friend(user, gamer):
    return not user.gamerprofile.blocked_by(gamer)


@predicate
def is_request_author(user, request):
    return request.requestor == user.gamerprofile


@predicate
def is_request_recipient(user, request):
    return user.gamerprofile == request.recipient


@predicate
def is_note_author(user, note):
    if note.author == user.gamerprofile:
        return True
    return False


rules.add_perm("community.list_communities", is_user)
rules.add_perm("community.view_details", is_community_member | is_public_community)
rules.add_perm("community.edit_community", is_community_admin)
rules.add_perm("community.join", is_joinable)
rules.add_perm("community.apply", is_eligible_applicant)
rules.add_perm("community.edit_application", is_applicant)
rules.add_perm("community.approve_application", is_application_approver)
rules.add_perm("community.review_applications", is_community_superior)
rules.add_perm("community.leave", is_membership_subject)
rules.add_perm("community.delete_community", is_community_owner)
rules.add_perm("community.kick_user", is_community_admin)
rules.add_perm("community.ban_user", is_community_admin)
rules.add_perm("community.edit_roles", is_community_admin)
rules.add_perm("community.edit_gamer_role", is_community_superior)
rules.add_perm("community.transfer_ownership", is_community_owner)
rules.add_perm("profile.view_detail", is_profile_viewer)
rules.add_perm("profile.can_friend", is_possible_friend)
rules.add_perm("profile.withdraw_friend_request", is_request_author)
rules.add_perm("profile.approve_friend_request", is_request_recipient)
rules.add_perm("profile.edit_profile", is_profile_owner)
rules.add_perm("profile.view_gamer_notes", is_note_author)
rules.add_perm("profile.remove_mute", is_muter)
