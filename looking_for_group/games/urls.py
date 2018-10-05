from django.urls import path
from schedule.feeds import CalendarICalendar, UpcomingEventsFeed
from schedule.views import api_occurrences

app_name = 'looking_for_group.games'

urlpatterns = [
    path('schedule/api/occurrences/', api_occurrences, name='api_occurrences'),
    path('schedule/feed/calendar/upcoming/<uuid:gamer>/', UpcomingEventsFeed(), name='upcoming_events_feed'),
    path('schedule/ical/calendar/<uuid:gamer>/', CalendarICalendar(), name='calendar_ical'),
]
