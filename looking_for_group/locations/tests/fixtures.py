import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Point

from ..models import Location

pytestmark = pytest.mark.django_db(transaction=True)


class LocationTData(object):
    """
    Fixture data object.
    """

    def __init__(self):
        self.loc_address = Location.objects.create(
            formatted_address="1600 Pennsylvania Ave NW, Washington, DC"
        )
        self.loc_place_id = Location.objects.create(
            google_place_id="ChIJFWTYAR1ZwokRYFUfwTY5kAI",
            google_place_name="Dag Hammarskjöld Library",
            formatted_address="",
        )
        # Willis Tower Skydeck
        self.loc_coords = Location.objects.create(
            geocode_method="reverse",
            latlong=Point(-87.6359, 41.8789),
            formatted_address="",
        )
        self.geocoded_location = Location.objects.create(
            google_place_name="Independence Hall",
            google_place_id="ChIJd8kca4PIxokRqW59OWceihQ",
            formatted_address="520 Chestnut St, Philadelphia, PA 19106",
            latlong=Point(-75.1550, 39.9489),
            geocode_attempts=1,
            country="United States",
            location_accuracy="ROOFTOP",
            state="Pennsylvania",
            city="Philadelphia",
            postal_code="19106",
            viewport_ne=Point(-75.1660, 39.9500),
            viewport_sw=Point(-75.0022, 39.9270),
        )


@pytest.fixture
def location_testdata(transactional_db):
    yield LocationTData()
    ContentType.objects.clear_cache()
