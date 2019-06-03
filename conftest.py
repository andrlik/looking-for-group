import sys

import pytest


@pytest.fixture(autouse=True)
def enable_db_access(db):
    pass


@pytest.fixture(autouse=True)
def firefox_options(firefox_options):
    firefox_options.headless = True
    return firefox_options


@pytest.fixture(autouse=True)
def selenium(selenium):
    selenium.implicitly_wait(10)
    yield selenium
    selenium.quit()


@pytest.fixture(scope="session")
def login_browser(selenium, usertologin, liveserver, password="password"):
    selenium.get(liveserver.url + "/accounts/login/")
    username_input = selenium.find_element_by_id("id_login")
    password_input = selenium.find_element_by_id("id_password")
    username_input.send_keys(usertologin.username)
    password_input.send_keys(password)
    selenium.find_element_by_xpath("//button[text()='Sign In']").click()
    yield selenium
    selenium.get(liveserver.url + "/accounts/logout/")
    selenium.find_element_by_xpath("//button[text()='Sign Out']").click()


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
