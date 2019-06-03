import pytest
from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from axe_selenium_python.axe import Axe
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from ..tests.test_views import BaseAbstractViewTest


def create_user(username="testuser", password="password"):
    user = get_user_model().objects.create(
        username=username, is_active=True, email="someone@example.com"
    )
    user.set_password(password)
    email, created = EmailAddress.objects.get_or_create(user=user, email=user.email)
    email.verified = True
    email.primary = True
    email.save()
    return user


# Begin Pytest conversions here ---------------------

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


def get_axe_violations(selenium, axe_options, url):
    selenium.get(url)
    axe = Axe(selenium)
    axe.inject()
    results = axe.run(options=axe_options)
    return axe, strip_out_false_positives(results["violations"])


@pytest.mark.parameterize("url_to_test", ["/", "/accounts/signin/"])
@pytest.mark.nondestructive
def basic_accessibility_test(liveserver, url_to_test):
    axe, violations = get_axe_violations(liveserver.url + url_to_test)
    assert len(violations) == 0, axe.report()


# Legacy tests start here. --------------------------


class BaseAccessibilityTest(object):

    usertologinas = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.axe_options = {"runOnly": ["wcag2a", "wcag2aa"]}
        ff_options = Options()
        ff_options.headless = True
        cls.selenium = webdriver.Firefox(options=ff_options)
        cls.selenium.implicitly_wait(10)

    def get(self, url):
        new_url = "{}{}".format(self.live_server_url, url)
        self.selenium.get(new_url)

    def login_browser(self):
        self.get("/accounts/login/")
        username_input = self.selenium.find_element_by_id("id_login")
        password_input = self.selenium.find_element_by_id("id_password")
        username_input.send_keys(self.usertologinas)
        password_input.send_keys("password")
        self.selenium.find_element_by_xpath("//button[text()='Sign In']").click()

    def logout_browser(self):
        self.get("/accounts/logout/")
        self.selenium.find_element_by_xpath("//button[text()='Sign Out']").click()

    def strip_out_false_positives(self, violations):
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

    def get_axe(self, url):
        self.selenium.get("{}{}".format(self.live_server_url, url))
        axe = Axe(self.selenium)
        axe.inject()
        return axe

    def get_axe_violations(self, url):
        axe = self.get_axe(url)
        results = axe.run(options=self.axe_options)
        violations = self.strip_out_false_positives(results["violations"])
        return axe, violations

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()


@pytest.mark.accessibility
@pytest.mark.nondestructive
class SimpleAccessibilityTest(BaseAccessibilityTest, StaticLiveServerTestCase):
    """
    Quick tests for main pages that are not tied to apps.
    """

    def setUp(self):
        user = create_user(username="testuser", password="password")
        self.usertologinas = user.username

    def test_root_page(self):
        axe, violations = self.get_axe_violations("/")
        assert len(violations) == 0, axe.report(violations)

    def test_signin_page(self):
        axe, violations = self.get_axe_violations("/accounts/signin/")
        assert len(violations) == 0, axe.report(violations)

    def test_signout_page(self):
        self.login_browser()
        axe, violations = self.get_axe_violations("/accounts/logout/")
        assert len(violations) == 0, axe.report(violations)


@pytest.mark.accessibility
@pytest.mark.nondestructive
class CatalogUrlTests(
    BaseAccessibilityTest, BaseAbstractViewTest, StaticLiveServerTestCase
):
    """
    Runs axe tests as a logged in user for each of the catalog urls.
    """

    def setUp(self):
        super().setUp()
        self.usertologinas = self.gamer1.username
        self.login_browser()

    def tearDown(self):
        # self.logout_browser()
        super().tearDown()

    def test_game_list(self):
        axe, violations = self.get_axe_violations(reverse("game_catalog:game-list"))
        assert len(violations) == 0, axe.report(violations)

    def test_system_list(self):
        axe, violations = self.get_axe_violations(reverse("game_catalog:system-list"))
        assert len(violations) == 0, axe.report(violations)

    def test_pub_list(self):
        axe, violations = self.get_axe_violations(reverse("game_catalog:pub-list"))
        assert len(violations) == 0, axe.report(violations)

    def test_module_list(self):
        axe, violations = self.get_axe_violations(reverse("game_catalog:module-list"))
        assert len(violations) == 0, axe.report(violations)

    def test_game_detail(self):
        axe, violations = self.get_axe_violations(self.numensource.get_absolute_url())
        assert len(violations) == 0, axe.report(violations)

    def test_edition_detail(self):
        axe, violations = self.get_axe_violations(self.numen.get_absolute_url())
        assert len(violations) == 0, axe.report(violations)

    def test_sourcebook_detail(self):
        axe, violations = self.get_axe_violations(self.numenbook.get_absolute_url())
        assert len(violations) == 0, axe.report(violations)

    def test_module_detail(self):
        axe, violations = self.get_axe_violations(self.cos.get_absolute_url())
        assert len(violations) == 0, axe.report(violations)

    def test_pub_detail(self):
        axe, violations = self.get_axe_violations(self.mcg.get_absolute_url())
        assert len(violations) == 0, axe.report(violations)

    def test_addition_add(self):
        axe, violations = self.get_axe_violations(
            reverse("game_catalog:addition_create", kwargs={"obj_type": "game"})
        )
        assert len(violations) == 0, axe.report(violations)

    def test_correction_add(self):
        axe, violations = self.get_axe_violations(
            reverse(
                "game_catalog:correction_create",
                kwargs={"objtype": "game", "object_id": self.numensource.pk},
            )
        )
        assert len(violations) == 0, axe.report(violations)
