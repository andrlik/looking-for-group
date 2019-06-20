import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("gamer_to_use", ["gamer1", "gamer4"])
def test_gm(client, game_testdata, django_assert_max_num_queries, gamer_to_use):
    gamer = getattr(game_testdata, gamer_to_use)
    with django_assert_max_num_queries(250):
        response = client.get(
            reverse("games:calendar_ical", kwargs={"gamer": gamer.pk})
        )
    assert response.status_code == 200
