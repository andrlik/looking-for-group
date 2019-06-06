import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

pytestmark = [pytest.mark.accessibility, pytest.mark.nondestructive]


def test_invite_create(
    myselenium, axe_class, live_server, login_method, invite_testdata
):
    login_method(myselenium, invite_testdata.gamer3.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "invites:invite_create",
            kwargs={
                "content_type": ContentType.objects.get_for_model(
                    invite_testdata.gp1
                ).pk,
                "slug": invite_testdata.gp1.slug,
            },
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results()["violations"]
    assert len(violations) == 0, axe.report(violations)


def test_invite_accept(
    myselenium, axe_class, live_server, login_method, invite_testdata
):
    login_method(myselenium, invite_testdata.gamer1.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "invites:invite_accept", kwargs={"invite": invite_testdata.invite1.slug}
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results()["violations"]
    assert len(violations) == 0, axe.report(violations)


def test_invite_delete(
    myselenium, axe_class, live_server, login_method, invite_testdata
):
    login_method(myselenium, invite_testdata.gamer3.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "invites:invite_delete", kwargs={"invite": invite_testdata.invite1.slug}
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results()["violations"]
    assert len(violations) == 0, axe.report(violations)
