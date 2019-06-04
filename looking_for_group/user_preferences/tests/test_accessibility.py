import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    "url_to_check",
    [
        reverse("user_preferences:setting-view"),
        reverse("user_preferences:setting-edit"),
        reverse("dashboard"),
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_views(
    myselenium,
    axe_class,
    axe_options,
    game_gamer_to_use,
    login_method,
    live_server,
    url_to_check,
):
    login_method(myselenium, game_gamer_to_use.user, live_server)
    myselenium.get(live_server.url + url_to_check)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)
