import pytest

from ...gamer_profiles.models import GamerProfile
from ...gamer_profiles.tests import factories
from ...user_preferences.models import Preferences


class AdminTData(object):
    def __init__(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        self.gamer4 = factories.GamerProfileFactory()
        self.admin_gamer = factories.GamerProfileFactory()
        self.admin_gamer.user.is_superuser = True
        self.admin_gamer.user.save()
        Preferences.objects.create(gamer=self.gamer1, notification_digest=True)
        Preferences.objects.create(gamer=self.gamer2, feedback_volunteer=True)
        for gamer in GamerProfile.objects.exclude(id__in=[self.gamer1.pk, self.gamer2.pk]):
            Preferences.objects.create(gamer=gamer)


@pytest.fixture
def admin_testdata():
    return AdminTData()
