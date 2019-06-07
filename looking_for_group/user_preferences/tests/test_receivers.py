import pytest

from ...gamer_profiles.models import CommunityMembership
from .. import models


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("not_setting", [True, False])
def test_add_member(game_testdata, not_setting):
    pref3 = models.Preferences.objects.create(gamer=game_testdata.gamer3)
    game_testdata.gamer3.refresh_from_db()
    pref3.community_subscribe_default = not_setting
    pref3.save()
    assert game_testdata.gamer3.preferences.community_subscribe_default == not_setting
    game_testdata.comm2.add_member(game_testdata.gamer3)
    assert (
        CommunityMembership.objects.get(
            gamer=game_testdata.gamer3, community=game_testdata.comm2
        ).game_notifications
        == not_setting
    )
