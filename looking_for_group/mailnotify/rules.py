import logging

import rules
from django.utils import timezone

from ..gamer_profiles.lookups import get_users_available_for_messaging

logger = logging.getLogger("rules")


def can_message_user(user, recipient):
    if recipient in get_users_available_for_messaging(user.gamerprofile):
        return True
    return False


def user_exchange_filter(sender, recipient, recipients_list):
    if not is_not_silenced(sender):
        return "You are currently silenced and cannot send messages."
    if not can_message_user(sender, recipient):
        return "is either not connected to you or has blocked you"
    return None


@rules.predicate
def is_not_silenced(user, obj=None):
    logger.debug("checking for silences")
    silences = user.silence_terms
    if silences.count() == 0:
        return True
    if silences.filter(ending__isnull=True).count() > 0:
        logger.debug("User is not silenced for eternity.")
        return False
    elif silences.filter(ending__gte=timezone.now()).count() > 0:
        logger.debug("user not is silenced for a term.")
        return False
    return True


@rules.predicate
def is_valid_sender_for_user(user, recipient):
    return can_message_user(user, recipient)


is_valid_sender = is_valid_sender_for_user & is_not_silenced


@rules.predicate
def is_admin(user, obj=None):
    return user.is_superuser


@rules.predicate
def is_report_creator(user, report):
    return user == report.reporter


@rules.predicate
def report_not_complete(user, report):
    return report.status != "complete"


is_user_report_editor = is_report_creator & report_not_complete

is_report_reader = is_admin | is_report_creator

is_report_deleter = is_admin | is_user_report_editor


rules.add_perm("postman.can_send_messages", is_not_silenced)
rules.add_perm("postman.can_message_user", is_valid_sender)
rules.add_perm("postman.report_view", is_report_reader)
rules.add_perm("postman.report_delete", is_report_deleter)
rules.add_perm("postman.view_report_list", is_admin)
rules.add_perm("postman.warn_plaintiff", is_admin)
rules.add_perm("postman.view_silenced", is_admin)
rules.add_perm("postman.silence_delete", is_admin)
rules.add_perm("postman.can_silence", is_admin)
