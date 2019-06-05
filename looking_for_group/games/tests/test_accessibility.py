import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    "url_to_check",
    [
        reverse("games:game_list"),
        reverse("games:my_game_list"),
        reverse("games:game_create"),
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_list_level_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    game_gamer_to_use,
    live_server,
    url_to_check,
):
    login_method(myselenium, game_gamer_to_use.user, live_server)
    myselenium.get(live_server.url + url_to_check)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.parametrize(
    "view_name",
    [
        "games:game_detail",
        "games:game_edit",
        "games:game_delete",
        "games:game_invite_list",
        "games:game_applicant_list",
        "games:session_list",
        "games:character_game_list",
        "games:session_adhoc_create",
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_game_level_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    game_gamer_to_use,
    live_server,
    game_game_to_use,
    view_name,
):
    login_method(myselenium, game_gamer_to_use, live_server)
    if "invite" in view_name:
        myselenium.get(
            live_server.url + reverse(view_name, kwargs={"slug": game_game_to_use.slug})
        )
    else:
        myselenium.get(
            live_server.url
            + reverse(view_name, kwargs={"gameid": game_game_to_use.slug})
        )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.parametrize(
    "view_name",
    [
        "games:session_detail",
        "games:session_edit",
        "games:session_move",
        "games:log_create",
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_session_level_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    game_gamer_to_use,
    live_server,
    game_session_to_use,
    view_name,
):
    login_method(myselenium, game_gamer_to_use, live_server)
    myselenium.get(
        live_server.url
        + reverse(view_name, kwargs={"session": game_session_to_use.slug})
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_character_level_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    game_gamer_to_use,
    live_server,
    game_character_to_use,
):
    login_method(myselenium, game_gamer_to_use, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "games:character_detail", kwargs={"character": game_character_to_use.slug}
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.parametrize("view_name", ["games:log_edit", "games:log_delete"])
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_log_level_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    game_gamer_to_use,
    live_server,
    game_log_to_use,
    view_name,
):
    login_method(myselenium, game_gamer_to_use, live_server)
    myselenium.get(
        live_server.url + reverse(view_name, kwargs={"log": game_log_to_use.slug})
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_game_apply(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    game_gamer_to_use,
    game_testdata,
    live_server,
):
    login_method(myselenium, game_gamer_to_use, live_server)
    myselenium.get(
        live_server.url
        + reverse("games:game_apply", kwargs={"gameid": game_testdata.gp3.slug})
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_calendar_view(
    myselenium, axe_class, live_server, game_gamer_to_use, login_method
):
    login_method(myselenium, game_gamer_to_use.user, live_server)
    myselenium.get(
        live_server.url
        + reverse("games:calendar_detail", kwargs={"gamer": game_gamer_to_use.username})
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results()["violations"]
    assert len(violations) == 0, axe.report(violations)
