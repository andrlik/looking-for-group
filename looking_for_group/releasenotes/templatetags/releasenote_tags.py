import logging

from django.template import Library

logger = logging.getLogger("releasenotes")

register = Library()


@register.inclusion_tag("releasenotes/rn.html")
def render_release_notes(release_note_list):
    return {"notes_to_render": release_note_list}


@register.simple_tag()
def update_latest_seen(user, release_note_list):
    if user.is_authenticated:
        logger.debug(
            "Received call to update lastest version shown for {}".format(user.username)
        )
        latest_note = release_note_list.latest("release_date")
        user.releasenotice.latest_vesion_shown = latest_note
        user.releasenotice.save()
