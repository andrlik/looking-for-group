import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.nondestructive
@pytest.mark.accessibility
def test_release_note_view(
    myselenium, axe_class, axe_options, login_method, rn_testdata, live_server
):
    url_to_check = reverse("releasenotes:note-list")
    login_method(myselenium, rn_testdata.gamer1.user, live_server)
    myselenium.get(live_server.url + url_to_check)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)
