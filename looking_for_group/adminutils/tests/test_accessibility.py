import pytest
from django.urls import reverse

pytestmark = [pytest.mark.accessibility, pytest.mark.nondestructive]


@pytest.mark.parametrize("url_to_check", [
    reverse("adminutils:notification"),
    reverse("adminutils:email"),
])
def test_notification_view(myselenium, axe_class, login_method, live_server, admin_testdata, url_to_check):
    login_method(myselenium, admin_testdata.admin_gamer.user, live_server)
    myselenium.get(live_server.url + url_to_check)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results()["violations"]
    assert len(violations) == 0, axe.report(violations)
