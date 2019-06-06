import pytest
from django.urls import reverse

# Begin Pytest conversions here ---------------------


@pytest.mark.parametrize("url_to_test", ["/", "/accounts/signin/"])
@pytest.mark.nondestructive
@pytest.mark.accessibility
def basic_accessibility_test(
    myselenium, axe_class, axe_options, live_server, url_to_test
):
    myselenium.get(live_server.url + url_to_test)
    axe = axe_class(myselenium)
    results = axe.get_axe_results(options=axe_options)
    assert len(results["violations"]) == 0, axe.report(results["violations"])


@pytest.mark.nondestructive
@pytest.mark.accessibility
def test_logout_page(
    myselenium, axe_class, axe_options, login_method, usertologinas, live_server
):
    login_method(myselenium, usertologinas, live_server)
    myselenium.get(live_server.url + "/accounts/logout/")
    axe = axe_class(myselenium)
    results = axe.get_axe_results(options=axe_options)
    assert len(results["violations"]) == 0, axe.report(results["violations"])


@pytest.mark.parametrize(
    "url_to_test",
    [
        reverse("game_catalog:game-list"),
        reverse("game_catalog:system-list"),
        reverse("game_catalog:pub-list"),
        reverse("game_catalog:module-list"),
        reverse("game_catalog:addition_create", kwargs={"obj_type": "game"}),
    ],
)
@pytest.mark.nondestructive
@pytest.mark.accessibility
def test_list_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    usertologinas,
    live_server,
    catalog_testdata,
    url_to_test,
):
    login_method(myselenium, usertologinas, live_server)
    myselenium.get(live_server.url + url_to_test)
    axe = axe_class(myselenium)
    results = axe.get_axe_results(options=axe_options)
    assert len(results["violations"]) == 0, axe.report(results["violations"])


@pytest.mark.nondestructive
@pytest.mark.accessibility
def test_detail_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    usertologinas,
    live_server,
    catalog_detail_url_to_check,
):
    login_method(myselenium, usertologinas, live_server)
    print("Checking url: {}".format(catalog_detail_url_to_check))
    myselenium.get(live_server.url + catalog_detail_url_to_check)
    axe = axe_class(myselenium)
    results = axe.get_axe_results(options=axe_options)
    assert len(results["violations"]) == 0, axe.report(results["violations"])


@pytest.mark.nondestructive
@pytest.mark.accessibility
def test_correction_create(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    usertologinas,
    catalog_testdata,
    live_server,
):
    login_method(myselenium, usertologinas, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "game_catalog:correction_create",
            kwargs={"objtype": "game", "object_id": catalog_testdata.numensource.pk},
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)
