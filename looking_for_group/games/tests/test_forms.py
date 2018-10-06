import pytest
from test_plus import TestCase

from ...gamer_profiles.tests.factories import GamerCommunityFactory, GamerProfileFactory
from ..forms import GamePostingForm, GameSessionForm, GameSessionRescheduleForm


class AbstractFormTest(TestCase):
    """
    Make our setup less tedious.
    """

    def setUp(self):
        self.gamer1 = GamerProfileFactory()
        self.gamer2 = GamerProfileFactory()
        self.gamer3 = GamerProfileFactory()
        self.comm1 = GamerCommunityFactory(owner=self.gamer1)
        self.comm2 = GamerCommunityFactory(owner=self.gamer2)
        self.gamer4 = GamerProfileFactory()


class GamePostingFormTest(AbstractFormTest):
    def test_commmunity_queryset(self):
        form = GamePostingForm(gamer=self.gamer1)
        assert form.fields["communities"].queryset.count() == 1
        assert form.fields["communities"].queryset.all()[0] == self.comm1
        self.comm2.add_member(self.gamer1)
        self.gamer1.refresh_from_db()
        form2 = GamePostingForm(gamer=self.gamer1)
        assert form2.fields["communities"].queryset.count() == 2
        assert self.comm2 in form2.fields["communities"].queryset.all()

    def test_invalid_call(self):
        with pytest.raises(KeyError):
            GamePostingForm()
