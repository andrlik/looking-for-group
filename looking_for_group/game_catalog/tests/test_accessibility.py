import pytest
from allauth.account.models import EmailAddress
from allauth.utils import get_user_model
from axe_selenium_python import Axe
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from .. import models
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


@pytest.mark.usefixtures("usertologinas")
class TDataCatalogObject(object):
    def __init__(self):
        self.mcg = models.GamePublisher(name="Monte Cook Games")
        self.mcg.save()
        self.wotc = models.GamePublisher(name="Wizards of the Coast")
        self.wotc.save()
        self.cypher = models.GameSystem(
            name="Cypher System", original_publisher=self.mcg
        )
        self.cypher.save()
        self.fivesrd = models.GameSystem(name="5E SRD", original_publisher=self.wotc)
        self.fivesrd.save()
        self.cypher.tags.add("player focused", "streamlined")
        self.fivesrd.tags.add("crunchy", "traditional")
        self.dd = models.PublishedGame.objects.create(title="Dungeons & Dragons")
        self.dd.tags.add("fantasy")
        self.ddfive = models.GameEdition(
            name="5E", game=self.dd, publisher=self.wotc, game_system=self.fivesrd
        )
        self.ddfive.save()
        self.numensource = models.PublishedGame(title="Numenera")
        self.numensource.save()
        self.numen = models.GameEdition.objects.create(
            name="1", game=self.numensource, publisher=self.mcg, game_system=self.cypher
        )
        self.numen.tags.add("weird", "future", "science fantasy")
        self.numenbook = models.SourceBook.objects.create(
            edition=self.numen, publisher=self.mcg, title="Numenera", corebook=True
        )
        self.cos = models.PublishedModule(
            title="Curse of Strahd",
            publisher=self.wotc,
            parent_game_edition=self.ddfive,
        )
        self.cos.save()
        self.cos.tags.add("horror")
        self.tiamat = models.PublishedModule(
            title="Rise of Tiamat", publisher=self.wotc, parent_game_edition=self.ddfive
        )
        self.tiamat.save()
        self.tiamat.tags.add("dragons")
        self.vv = models.PublishedModule(
            title="Into the Violet Vale",
            publisher=self.mcg,
            parent_game_edition=self.numen,
        )
        self.vv.save()
        self.strange_source = models.PublishedGame.objects.create(title="The Strange")
        self.strange = models.GameEdition(
            name="1",
            publisher=self.mcg,
            game=self.strange_source,
            game_system=self.cypher,
        )
        self.strange.save()


@pytest.fixture
def testdata(transactional_db):
    """
    Override the existing feature and load the additional data to the DB, but return the same fixture value.
    """
    return TDataCatalogObject()


@pytest.fixture(params=["mcg", "cypher", "numensource", "numen", "numenbook", "vv"])
def catalog_detail_url_to_check(request, testdata):
    return getattr(testdata, request.param).get_absolute_url()


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
    testdata,
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
    testdata,
    live_server,
):
    login_method(myselenium, usertologinas, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "game_catalog:correction_create",
            kwargs={"objtype": "game", "object_id": testdata.numensource.pk},
        )
    )
    axe = axe_class(myselenium)
    results = axe.get_axe_results(options=axe_options)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


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
