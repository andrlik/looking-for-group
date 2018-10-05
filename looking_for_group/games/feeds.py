from django.contrib.syndication.views import FeedDoesNotExist
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from schedule.feeds import ICalendarFeed, UpcomingEventsFeed

from ..gamer_profiles.models import GamerProfile
from .models import Calendar


class UpcomingGamesFeed(UpcomingEventsFeed):

    def get_object(self, request, gamer):
        profile = get_object_or_404(GamerProfile, pk=gamer)
        calendar, created = Calendar.objects.get_or_create(slug=profile.username, defaults={'name': "{}'s Calendar".format(profile.username)})
        return calendar

    def feed_title(self, obj):
        return "Game Schedule for {}".format(obj.slug)

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return reverse_lazy('games:calendar', kwargs={'gamer': GamerProfile.objects.get(username=obj.slug).pk})


class GamesICalFeed(ICalendarFeed):

    def items(self):
        gamer_id = self.args[1]
        gamer = get_object_or_404(GamerProfile, pk=gamer_id)
        cal, created = Calendar.objects.get_or_create(slug=gamer.username, defaults={'name': "{}'s Calendar".format(gamer.username)})
        return cal.events.all()
