import logging

from django.template import Library

from ..signals import user_specific_notes_displayed

logger = logging.getLogger("releasenotes")

register = Library()


@register.inclusion_tag("releasenotes/rn.html")
def render_release_notes(release_note_list):
    return {"notes_to_render": release_note_list}


@register.simple_tag(takes_context=True)
def update_latest_seen(context, user, release_note_list=None):
    logger.debug("Received call to update latest version shown...")
    if user.is_authenticated and release_note_list:
        logger.debug(
            "Firing signal to update user records based on note set {}".format(
                release_note_list
            )
        )
        user_specific_notes_displayed.send(
            sender=type(user),
            user=user,
            note_list=release_note_list,
            request=context["request"],
        )
    else:
        logger.debug(
            "User is not authenticated or there are no missing release notes to show them."
        )
