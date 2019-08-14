import pytest

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "object_to_test,expected_result",
    [
        ("loc_address", False),
        ("loc_place_id", False),
        ("loc_coords", False),
        ("geocoded_location", True),
    ],
)
def test_geocoded_detection(location_testdata, object_to_test, expected_result):
    """
    Checks that the system properly identifies a geocoded address vs a non-geocoded address.
    """
    loc = getattr(location_testdata, object_to_test)
    assert loc.is_geocoded == expected_result


@pytest.mark.parametrize(
    "object_to_test,start_attempts,expected_attempts,expected_address_value,expected_city,expected_state,expected_postal_code,expected_country",
    [
        (
            "loc_address",
            0,
            1,
            "1600 Pennsylvania Ave NW",
            "Washington",
            "District of Columbia",
            "20500",
            "United States",
        ),
        (
            "loc_place_id",
            0,
            1,
            "405 E 42nd St",
            "New York",
            "New York",
            "10017",
            "United States",
        ),
        (
            "loc_coords",
            0,
            1,
            "233 S Wacker Dr",
            "Chicago",
            "Illinois",
            "60606",
            "United States",
        ),
        (
            "geocoded_location",
            1,
            1,
            "Chestnut St",
            "Philadelphia",
            "Pennsylvania",
            "19106",
            "United States",
        ),
    ],
)
def test_geocode_locations(
    location_testdata,
    object_to_test,
    start_attempts,
    expected_attempts,
    expected_address_value,
    expected_city,
    expected_state,
    expected_postal_code,
    expected_country,
):
    """
    For some of the locations already in the database, try to geocode them.
    """
    loc = getattr(location_testdata, object_to_test)
    assert loc.geocode_attempts == start_attempts
    loc.geocode()
    loc.refresh_from_db()
    assert loc.is_geocoded
    assert loc.geocode_attempts == expected_attempts
    assert loc.latlong
    assert loc.viewport_ne
    assert loc.viewport_sw
    assert expected_address_value in loc.formatted_address
    assert loc.location_accuracy
    assert loc.google_place_id
    assert loc.city == expected_city
    assert loc.state == expected_state
    assert loc.postal_code == expected_postal_code
    assert loc.country == expected_country
