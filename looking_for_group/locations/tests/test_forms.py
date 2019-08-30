import pytest
from django.forms import HiddenInput

from ..forms import LocationForm

pytestmark = [pytest.mark.django_db(transaction=True)]


def test_blank_form_render():
    form = LocationForm()
    assert isinstance(form.fields["google_place_id"].widget, HiddenInput)


def test_instance_form_render(location_testdata):
    print(location_testdata.loc_address.formatted_address)
    assert LocationForm(instance=location_testdata.loc_address)
