import sys

import pytest
from axe_selenium_python import Axe
from django.contrib.contenttypes.models import ContentType

from looking_for_group.adminutils.tests.fixtures import *  # noqa
from looking_for_group.game_catalog.tests.fixtures import *  # noqa
from looking_for_group.gamer_profiles.tests import factories
from looking_for_group.gamer_profiles.tests.fixtures import *  # noqa
from looking_for_group.games.tests.fixtures import *  # noqa
from looking_for_group.invites.tests.fixtures import *  # noqa
from looking_for_group.locations.tests.fixtures import *  # noqa
from looking_for_group.rpgcollections.tests.fixtures import *  # noqa


class MyAxe(Axe):
    """
    Same as base class but strips out results.
    """

    def strip_out_false_positives(self, violations):
        """
        Cleans an axe instance of false positives.
        """

        x = 0
        ids_to_remove = []
        if len(violations) == 0:
            return violations
        for viol in violations:
            if (
                viol["id"] == "label"
                and len(viol["nodes"][0]["target"]) == 1
                and viol["nodes"][0]["target"][0] == "#id_q"
            ):
                ids_to_remove.append(x)
            if (
                viol["id"] == "color-contrast"
                and len(viol["nodes"][0]["target"]) == 1
                and len(viol["nodes"][0]["any"]) == 1
                and "#1779ba" in viol["nodes"][0]["any"][0]["message"]
                and "#2c3840" in viol["nodes"][0]["any"][0]["message"]
            ):
                ids_to_remove.append(x)
            x += 1
        for idr in reversed(ids_to_remove):
            del violations[idr]
        return violations

    def get_axe_results(self, options={"runOnly": ["wcag2a", "wcag2aa"]}):
        """
        Strips out false positives.
        """
        self.inject()
        results = self.run(options=options)
        results["violations"] = self.strip_out_false_positives(results["violations"])
        return results


@pytest.mark.django_db(transaction=True)
@pytest.fixture
def base_db_gamers():
    ContentType.objects.clear_cache()
    gamer1 = factories.GamerProfileFactory()
    gamer2 = factories.GamerProfileFactory()
    gamer3 = factories.GamerProfileFactory()
    gamer4 = factories.GamerProfileFactory()
    gamers = [gamer1, gamer2, gamer3, gamer4]
    yield gamers


@pytest.fixture
def usertologinas(base_db_gamers):
    return base_db_gamers[0].user


@pytest.fixture(autouse=True)
def axe_class():
    return MyAxe


@pytest.fixture(autouse=True)
def enable_db_access(db):
    pass


def login_redirect_check(response):
    return response.status_code == 302 and "/accounts/login/" in response["Location"]


@pytest.fixture
def assert_login_redirect():
    return login_redirect_check


@pytest.fixture(autouse=True)
def firefox_options(firefox_options):
    firefox_options.headless = True
    return firefox_options


@pytest.fixture
def myselenium(selenium):
    selenium.implicitly_wait(10)
    yield selenium
    selenium.quit()


def browser_login(myselenium, usertologin, live_server, password="password"):
    myselenium.get(live_server.url + "/accounts/login/")
    username_input = myselenium.find_element_by_id("id_login")
    password_input = myselenium.find_element_by_id("id_password")
    username_input.send_keys(usertologin.username)
    password_input.send_keys(password)
    myselenium.find_element_by_xpath("//button[text()='Sign In']").click()


def browser_logout(myselenium, live_server):
    myselenium.get(live_server.url + "/accounts/logout/")
    myselenium.find_element_by_xpath("//button[text()='Sign Out']").click()


@pytest.fixture(autouse=True)
def login_method():
    return browser_login


@pytest.fixture(autouse=True)
def logout_method():
    return browser_logout


@pytest.fixture(autouse=True)
def axe_options():
    return {"runOnly": ["wcag2a", "wcag2aa"]}


def pytest_addoption(parser):
    parser.addoption(
        "--a11y", action="store_true", default=False, help="run only a11y tests"
    )


def pytest_collection_modifyitems(config, items):
    x = 0
    if config.getoption("--a11y"):
        skip_a11y = pytest.mark.skip(reason="Only run accessibile tests")
        print("Preparing to only run accessbility tests")
        for item in items:
            accessible = False
            if "accessibility" in item.keywords:
                accessible = True
            else:
                # print("Marking test {} as skippable".format(item.name))
                item.add_marker(skip_a11y)
            if accessible:
                x += 1
            # print("{}-{}: {}".format(item.fspath, item.name, [marker for marker in item.iter_markers()]))
    else:
        skip_a11y = pytest.mark.skip("Only run non-accessibility tests")
        print("Preparing to run non-accessbile tests.")
        for item in items:
            accessible = False
            if "accessibility" in item.keywords:
                accessible = True
                item.add_marker(skip_a11y)
                x += 1
    print("Found {} accessbile tests".format(x))
    sys.stdout.flush()
