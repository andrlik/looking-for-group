import pytest

pytestmark = [pytest.mark.accessibility, pytest.mark.nondestructive]


def test_collections_detail_views(myselenium, axe_class, login_method, live_server, collection_testdata, collection_detail_url):
    login_method(myselenium, collection_testdata.gamer1.user, live_server)
    myselenium.get(live_server.url + collection_detail_url)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results()["violations"]
    assert len(violations) == 0, axe.report(violations)
