from datetime import datetime, timedelta

import pytz
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
                title="Avail {}".format(i)
            )
            Event.objects.create(
                calendar=self.cal2,
                start=make_event_time_for_date(self.weekdays[i], "12:00"),
                end=make_event_time_for_date(self.weekdays[i], "17:00"),
                rule=self.weeklyrule,
                title="Avail {}".format(i)
            )
            Event.objects.create(
                calendar=self.cal3,
                start=make_event_time_for_date(self.weekdays[i], "10:00"),
                end=make_event_time_for_date(self.weekdays[i], "15:00"),
                rule=self.weeklyrule,
                title="Avail {}".format(i)
            )
        for i in [5, 6]:
            Event.objects.create(
                calendar=self.cal4,
                start=make_event_time_for_date(self.weekdays[i], "00:00"),
                end=make_event_time_for_date(self.weekdays[i], "23:59"),
                rule=self.weeklyrule,
                title="Avail {}".format(i)
            )
        Event.objects.create(
            calendar=self.cal4,
            start=make_event_time_for_date(self.weekdays[3], "12:00"),
            end=make_event_time_for_date(self.weekdays[3], "14:00"),
            rule=self.weeklyrule,
            title="extraavail"
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


class TestUpdateAvailView(AbstractAvailTestCase):
    """
    Try to use the view for updating availability.
    """

    def setUp(self):
        super().setUp()
        self.view_name = "gamer_profiles:set-available"
        self.new_avail_data = {
            "monday_all_day": 1,
            "monday_earliest": "",
            "monday_latest": "14:50",  # should be ignored
            "tuesday_earliest": "",
            "tuesday_latest": "",
            "wednesday_earliest": "",
            "wednesday_latest": "",
            "thursday_earliest": "",
            "thursday_latest": "",
            "friday_all_day": 1,
            "friday_earliest": "",
            "friday_latest": "",
            "saturday_earliest": "10:00",
            "saturday_latest": "15:00",
            "sunday_earliest": "10:00",
            "sunday_latest": "17:00"
        }
        self.incomplete_start_end = {
            "monday_all_day": 1,
            "monday_earliest": "",
            "monday_latest": "14:50",  # should be ignored
            "tuesday_earliest": "",
            "tuesday_latest": "",
            "wednesday_earliest": "15:00",
            "wednesday_latest": "",
            "thursday_earliest": "",
            "thursday_latest": "17:00",
            "friday_all_day": 1,
            "friday_earliest": "",
            "friday_latest": "",
            "saturday_earliest": "10:00",
            "saturday_latest": "15:00",
            "sunday_earliest": "10:00",
            "sunday_latest": "17:00"
        }
        self.times_wrong = {
            "monday_all_day": 1,
            "monday_earliest": "",
            "monday_latest": "14:50",  # should be ignored
            "tuesday_earliest": "",
            "tuesday_latest": "",
            "wednesday_earliest": "17:00",
            "wednesday_latest": "13:00",
            "thursday_earliest": "",
            "thursday_latest": "",
            "friday_all_day": 1,
            "friday_earliest": "",
            "friday_latest": "",
            "saturday_earliest": "10:00",
            "saturday_latest": "15:00",
            "sunday_earliest": "10:00",
            "sunday_latest": "17:00"
        }

    def test_login_required(self):
        self.assertLoginRequired(self.view_name)

    def test_load_correctly(self):
        with self.login(username=self.gamer1.username):
            self.assertGoodView(self.view_name)

    def test_backwards_times(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.times_wrong)
            self.response_200()
            error_list = self.get_context('form').errors
            assert len(error_list) == 1

    def test_incomplete_times(self):
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.incomplete_start_end)
            self.response_200()
            error_list = self.get_context('form').errors
            assert len(error_list) == 2

    def test_successful_post(self):
        eastern = pytz.timezone("America/New_York")
        with self.login(username=self.gamer1.username):
            self.post(self.view_name, data=self.new_avail_data)
            if self.last_response.status_code == 200:
                self.print_form_errors()
            self.response_302()
            occs = self.cal1.get_next_week_occurrences()
            for occ in occs:
                print("testing for weekday num {}".format(occ.start.weekday()))
                if occ.start.weekday() == 0:
                    print("Mon start:"+occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "00:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "23:59"
                assert occ.start.weekday() not in [1, 2, 3]
                assert occ.start.weekday() in [0, 4, 5, 6]
                if occ.start.weekday() == 4:
                    print("Friday start:"+occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "00:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "23:59"
                if occ.start.weekday() == 5:
                    print("Sat start:"+occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "10:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "15:00"
                if occ.start.weekday() == 6:
                    print("Sun start:"+occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "10:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "17:00"
