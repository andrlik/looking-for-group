from datetime import datetime, timedelta

import pytest
import pytz
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from schedule.models import Event, Rule

from ...gamer_profiles.models import GamerProfile
from ..models import AvailableCalendar
from ..tests.fixtures import GamesTData

pytestmark = pytest.mark.django_db(transaction=True)


def make_event_time_for_date(date_to_use, time_string):
    return datetime.strptime(
        "{} {} {}".format(
            date_to_use.strftime("%Y-%m-%d"), time_string, date_to_use.strftime("%z")
        ),
        "%Y-%m-%d %H:%M %z",
    )


class AvailTData(GamesTData):
    def __init__(self):
        super().__init__()
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
                title="Avail {}".format(i),
            )
            Event.objects.create(
                calendar=self.cal2,
                start=make_event_time_for_date(self.weekdays[i], "12:00"),
                end=make_event_time_for_date(self.weekdays[i], "17:00"),
                rule=self.weeklyrule,
                title="Avail {}".format(i),
            )
            Event.objects.create(
                calendar=self.cal3,
                start=make_event_time_for_date(self.weekdays[i], "10:00"),
                end=make_event_time_for_date(self.weekdays[i], "15:00"),
                rule=self.weeklyrule,
                title="Avail {}".format(i),
            )
        for i in [5, 6]:
            Event.objects.create(
                calendar=self.cal4,
                start=make_event_time_for_date(self.weekdays[i], "00:00"),
                end=make_event_time_for_date(self.weekdays[i], "23:59"),
                rule=self.weeklyrule,
                title="Avail {}".format(i),
            )
        Event.objects.create(
            calendar=self.cal4,
            start=make_event_time_for_date(self.weekdays[3], "12:00"),
            end=make_event_time_for_date(self.weekdays[3], "14:00"),
            rule=self.weeklyrule,
            title="extraavail",
        )


@pytest.fixture
def avail_testdata():
    ContentType.objects.clear_cache()
    yield AvailTData()
    ContentType.objects.clear_cache()


@pytest.mark.parametrize(
    "cal, start_time, end_time, overlap, expected_result",
    [
        ("cal1", "17:00", "19:00", None, False),  # Match
        ("cal1", "10:00", "12:00", None, True),  # Non-match
        ("cal1", "15:00", "17:00", 120, True),  # Overlap insufficient
        ("cal1", "19:00", "21:00", 120, True),  # Overlap insufficent
        ("cal1", "15:00", "17:00", 30, False),  # Overlap sufficient
        ("cal1", "19:00", "21:00", 120, True),  # Overlap insufficient
        ("cal4", "12:00", "15:00", None, True),  # No availability.
    ],
)
def test_direct_query(
    avail_testdata, cal, start_time, end_time, overlap, expected_result
):
    cal_to_use = getattr(avail_testdata, cal)
    if expected_result:
        assert cal_to_use.check_proposed_time(
            make_event_time_for_date(avail_testdata.weekdays[1], start_time),
            make_event_time_for_date(avail_testdata.weekdays[1], end_time),
            minimum_overlap=overlap,
        )
    else:
        assert not cal_to_use.check_proposed_time(
            make_event_time_for_date(avail_testdata.weekdays[1], start_time),
            make_event_time_for_date(avail_testdata.weekdays[1], end_time),
            minimum_overlap=overlap,
        )


@pytest.mark.parametrize(
    "cal_to_use, gamer_to_use, expected_matches",
    [
        ("cal1", "gamer1", 3),
        ("cal2", "gamer2", 4),
        ("cal3", "gamer3", 4),
        ("cal4", "gamer4", 5),
    ],
)
def test_list_query(avail_testdata, cal_to_use, gamer_to_use, expected_matches):
    gamer = getattr(avail_testdata, gamer_to_use)
    cal = getattr(avail_testdata, cal_to_use)
    gamers = GamerProfile.objects.exclude(id=gamer.id)
    matches = AvailableCalendar.objects.find_compatible_schedules(cal, gamers)
    assert len(matches) == expected_matches


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, post_data, expected_post_response, expected_form_errors",
    [
        (None, 302, None, None, None),  # Requires login
        (
            "gamer1",
            200,
            {
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
                "sunday_latest": "17:00",
            },
            200,
            1,
        ),  # Times are backwards
        (
            "gamer1",
            200,
            {
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
                "sunday_latest": "17:00",
            },
            200,
            2,
        ),  # Times are incomplete
        (
            "gamer1",
            200,
            {
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
                "sunday_latest": "17:00",
            },
            302,
            None,
        ),
    ],
)
def test_availability_update_view(
    client,
    avail_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    post_data,
    expected_post_response,
    expected_form_errors,
):
    if gamer_to_use:
        gamer = getattr(avail_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse("gamer_profiles:set-available")
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 200:
            assert expected_form_errors == len(response.context["form"].errors)
        if expected_post_response == 302:
            eastern = pytz.timezone("America/New_York")
            occs = avail_testdata.cal1.get_next_week_occurrences()
            for occ in occs:
                print("testing for weekday num {}".format(occ.start.weekday()))
                if occ.start.weekday() == 0:
                    print("Mon start:" + occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "00:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "23:59"
                assert occ.start.weekday() not in [1, 2, 3]
                assert occ.start.weekday() in [0, 4, 5, 6]
                if occ.start.weekday() == 4:
                    print("Friday start:" + occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "00:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "23:59"
                if occ.start.weekday() == 5:
                    print("Sat start:" + occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "10:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "15:00"
                if occ.start.weekday() == 6:
                    print("Sun start:" + occ.start.strftime("%H:%M%z"))
                    assert occ.start.astimezone(eastern).strftime("%H:%M") == "10:00"
                    assert occ.end.astimezone(eastern).strftime("%H:%M") == "17:00"
