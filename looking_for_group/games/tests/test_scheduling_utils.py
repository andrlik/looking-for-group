from datetime import datetime, timedelta

from django.utils import timezone
from schedule.models import Event, Rule

from ...gamer_profiles.models import GamerProfile
from ..models import AvailableCalendar
from .test_views import AbstractViewTestCaseSignals


def make_event_time_for_date(date_to_use, time_string):
    return datetime.strptime(
        "{} {} {}".format(
            date_to_use.strftime("%Y-%m-%d"), time_string, date_to_use.strftime("%z")
        ),
        "%Y-%m-%d %H:%M %z",
    )


class AbstractAvailTestCase(AbstractViewTestCaseSignals):
    def setUp(self):
        super().setUp()
        self.weeklyrule, created = Rule.objects.get_or_create(
            name="weekly", defaults={"description": "Weekly", "frequency": "WEEKLY"}
        )
        self.cal1 = AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
            self.gamer1
        )
        self.cal2 = AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
            self.gamer2
        )
        self.cal3 = AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
            self.gamer3
        )
        self.cal4 = AvailableCalendar.objects.get_or_create_availability_calendar_for_gamer(
            self.gamer4
        )
        # Define an available time for each day of the week
        today_weekday = (timezone.now() + timedelta(days=7)).weekday()
        self.weekdays = []
        monday = timezone.now() - timedelta(days=today_weekday)
        self.weekdays.append(monday)
        self.weekdays.append(monday + timedelta(days=1))
        self.weekdays.append(monday + timedelta(days=2))
        self.weekdays.append(monday + timedelta(days=3))
        self.weekdays.append(monday + timedelta(days=4))
        self.weekdays.append(monday + timedelta(days=5))
        self.weekdays.append(monday + timedelta(days=6))
        for i in range(6):
            Event.objects.create(
                calendar=self.cal1,
                start=make_event_time_for_date(self.weekdays[i], "16:00"),
                end=make_event_time_for_date(self.weekdays[i], "20:00"),
                rule=self.weeklyrule,
            )
            Event.objects.create(
                calendar=self.cal2,
                start=make_event_time_for_date(self.weekdays[i], "12:00"),
                end=make_event_time_for_date(self.weekdays[i], "17:00"),
                rule=self.weeklyrule,
            )
            Event.objects.create(
                calendar=self.cal3,
                start=make_event_time_for_date(self.weekdays[i], "10:00"),
                end=make_event_time_for_date(self.weekdays[i], "15:00"),
                rule=self.weeklyrule,
            )
        for i in [5, 6]:
            Event.objects.create(
                calendar=self.cal4,
                start=make_event_time_for_date(self.weekdays[i], "00:00"),
                end=make_event_time_for_date(self.weekdays[i], "23:59"),
                rule=self.weeklyrule,
            )
        Event.objects.create(
            calendar=self.cal3,
            start=make_event_time_for_date(self.weekdays[5], "12:00"),
            end=make_event_time_for_date(self.weekdays[5], "14:00"),
            rule=self.weeklyrule,
        )


class DirectQueryTest(AbstractAvailTestCase):
    def test_player_self_match(self):
        assert not self.cal1.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "17:00"),
            make_event_time_for_date(self.weekdays[1], "19:00"),
        )

    def test_player_non_match(self):
        assert self.cal1.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "10:00"),
            make_event_time_for_date(self.weekdays[1], "12:00"),
        )

    def test_overlap_insufficient(self):
        assert self.cal1.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "15:00"),
            make_event_time_for_date(self.weekdays[1], "17:00"),
            minimum_overlap=120,
        )
        assert self.cal1.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "19:00"),
            make_event_time_for_date(self.weekdays[1], "21:00"),
            minimum_overlap=120,
        )

    def test_overlap_sufficient(self):
        assert not self.cal1.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "15:00"),
            make_event_time_for_date(self.weekdays[1], "17:00"),
            minimum_overlap=30,
        )

    def test_overlap_not_sufficient(self):
        assert self.cal1.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "19:00"),
            make_event_time_for_date(self.weekdays[1], "21:00"),
            minimum_overlap=120,
        )

    def test_no_availability(self):
        assert self.cal4.check_proposed_time(
            make_event_time_for_date(self.weekdays[1], "12:00"),
            make_event_time_for_date(self.weekdays[1], "15:00"),
        )


class ListQueryTests(AbstractAvailTestCase):
    def test_for_player1(self):
        gamers = GamerProfile.objects.exclude(id=self.gamer1.id)
        matches = AvailableCalendar.objects.find_compatible_schedules(self.cal1, gamers)
        assert len(matches) == 1

    def test_for_player2(self):
        gamers = GamerProfile.objects.exclude(id=self.gamer2.id)
        matches = AvailableCalendar.objects.find_compatible_schedules(self.cal2, gamers)
        assert len(matches) == 2

    def test_for_player3(self):
        gamers = GamerProfile.objects.exclude(id=self.gamer3.id)
        matches = AvailableCalendar.objects.find_compatible_schedules(self.cal3, gamers)
        assert len(matches) == 2

    def test_for_player4(self):
        gamers = GamerProfile.objects.exclude(id=self.gamer4.id)
        matches = AvailableCalendar.objects.find_compatible_schedules(self.cal4, gamers)
        assert len(matches) == 3
