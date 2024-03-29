from datetime import timedelta

import icalendar
import pytz
from django.contrib.syndication.views import FeedDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from schedule.feeds import CalendarICalendar, UpcomingEventsFeed
from schedule.feeds.ical import EVENT_ITEMS

from ..gamer_profiles.models import GamerProfile
from .models import Calendar, GameEvent, GamePosting, Occurrence


class UpcomingGamesFeed(UpcomingEventsFeed):
    def get_object(self, request, gamer):
        profile = get_object_or_404(GamerProfile, pk=gamer)
        calendar, created = Calendar.objects.get_or_create(
            slug=profile.username,
            defaults={"name": "{}'s Calendar".format(profile.username)},
        )
        return calendar

    def feed_title(self, obj):
        return "Game Schedule for {}".format(obj.slug)

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return reverse_lazy(
            "games:calendar",
            kwargs={"gamer": GamerProfile.objects.get(username=obj.slug).pk},
        )


class GamesICalFeed(CalendarICalendar):

    i = 1

    def items(self):
        tz = pytz.timezone("UTC")
        gamer_id = self.kwargs["gamer"]
        gamer = get_object_or_404(GamerProfile, pk=gamer_id)
        cal, created = Calendar.objects.get_or_create(
            slug=gamer.username,
            defaults={"name": "{}'s Calendar".format(gamer.username)},
        )
        if gamer.user.timezone:
            tz = pytz.timezone(gamer.user.timezone)
        return cal.occurrences_after(timezone.now().astimezone(tz) - timedelta(days=30))

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        cal = icalendar.Calendar()
        cal.add("prodid", "-// lfg-directory //")
        cal.add("version", "2.0")

        end_date = timezone.now() + timedelta(days=400)
        if Occurrence.objects.all().count() > 0:
            self.i = Occurrence.objects.latest("id").id + 1
        for item in self.items():
            if self.item_start(item) >= end_date:
                break
            event = icalendar.Event()

            for vkey, key in EVENT_ITEMS:
                value = getattr(self, "item_" + key)(item)
                if value:
                    event.add(vkey, value)
            event.add("status", self.item_status(item))
            cal.add_component(event)

        response = HttpResponse(cal.to_ical())
        response["Content-Type"] = "text/calendar"
        return response

    def item_uid(self, item):
        if item.id:
            uid = str(item.id + self.i)
            self.i += 1
        else:
            uid = item.id
        return uid

    def item_location(self, item):
        ge = GameEvent.objects.get(pk=item.event.id)
        if ge.is_master_event():
            game = GamePosting.objects.get(event=ge)
        else:
            game = GamePosting.objects.get(event=ge.get_master_event())
        if game.game_mode == "irl" and game.game_location:
            return "{} (https://app.lfg.directory{})".format(
                game.game_location.formatted_address, str(game.get_absolute_url())
            )
        return "https://app.lfg.directory" + str(game.get_absolute_url())

    def item_status(self, item):
        if item.cancelled:
            return "CANCELLED"
        return "CONFIRMED"
