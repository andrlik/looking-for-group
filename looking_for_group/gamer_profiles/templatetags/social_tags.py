from collections import OrderedDict

import pytz
from django.db.models.query_utils import Q
from django.template import Library
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from schedule.models import Calendar

from .. import models

register = Library()


@register.simple_tag(takes_context=True)
def community_role_flag(context, community):
    """
    Takes an instance of community and returns the current user's role
    in it as an HTML span, if applicable.
    """
    if (
        not isinstance(community, models.GamerCommunity)
        or not context["request"].user.is_authenticated
    ):
        return ""
    try:
        role = community.get_role(context["request"].user.gamerprofile)
    except models.NotInCommunity:
        role = None
    if role:
        extra_class = "secondary"
        if role == "Admin":
            extra_class = "primary"
        return format_html("<span class='membership label {}'>{}</span>", extra_class, role)
    else:
        if community.private:
            return format_html(
                "<a href='{}' class='button small'>Apply</a>",
                reverse(
                    "gamer_profiles:community-apply", kwargs={"community": community.pk}
                ),
            )
        else:
            return format_html(
                "<a href='{}' class='button small'>Join</a>",
                reverse(
                    "gamer_profiles:community-join", kwargs={"community": community.pk}
                ),
            )


@register.simple_tag(takes_context=True)
def is_blocked_by_user(context, gamer):
    '''
    Takes a gamer profile as an argument and compares to request.user. If gamer is blocked by request.user, then retun True.
    Should be assigned to a variable, e.g. {% is_blocked_by_gamer gamer as blocked %}
    '''
    block_record = models.BlockedUser.objects.filter(blockee=gamer, blocker=context['user'].gamerprofile)
    if block_record.count() > 0:
        return True
    return False


@register.simple_tag()
def get_conflicts(gamer, game, user_timezone=pytz.timezone('UTC')):
    """
    For a given gamer and game, retrieve events excluding the game events.
    """
    end_recur_empty_q = Q(rule__isnull=False, end_recurring_period__isnull=True)
    end_recur_future_q = Q(rule__isnull=False, end_recurring_period__gt=timezone.now())
    one_shot_q = Q(rule__isnull=True, start__gt=timezone.now())
    cal, created = Calendar.objects.get_or_create(slug=gamer.username, defaults={"name": "{}'s calendar".format(gamer.username)})
    cal_events = cal.events.filter(end_recur_future_q | end_recur_empty_q | one_shot_q)
    player_result = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }
    if game.event:
        cal_events = cal_events.exclude(id__in=[e.id for e in game.event.get_child_events()])
    if cal_events.count() == 0:
        return player_result
    else:
        occ = None
        for event in cal_events:
            occ_future = event.occurrences_after()
            try:
                occ = next(occ_future)
                while occ.cancelled:
                    occ = next(occ_future)
            except StopIteration:
                pass
            player_result[event.start.astimezone(user_timezone).strftime("%A")].append({'event': event, 'next': occ})
        return player_result


@register.simple_tag()
def get_weekday_list():
    return [_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")]


@register.simple_tag(takes_context=True)
def get_gamer_scheduling_dict(context, game):
    user_timezone = pytz.timezone(context['request'].user.timezone)
    result = OrderedDict()
    for gamer in game.players.all():
        result[gamer.username] = {
            "gamer": gamer,
            "avail": gamer.get_availability(),
            "conflicts": get_conflicts(gamer, game, user_timezone),
        }
    return result
