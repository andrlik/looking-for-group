import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    "url_to_check",
    [
        reverse("helpdesk:issue-list"),
        reverse("helpdesk:my-issue-list"),
        reverse("helpdesk:issue-create"),
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_issue_list_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    helpdesk_testdata,
    live_server,
    url_to_check,
):
    gamer = getattr(helpdesk_testdata, "gamer1")
    login_method(myselenium, gamer.user, live_server)
    myselenium.get(live_server.url + url_to_check)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.parametrize("issue_to_use", ["issue1", "issue4"])
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_issue_detail_view(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    helpdesk_testdata,
    issue_to_use,
    live_server,
):
    gamer = getattr(helpdesk_testdata, "gamer1")
    login_method(myselenium, gamer.user, live_server)
    myselenium.get(
        live_server.url
        + str(getattr(helpdesk_testdata, issue_to_use).get_absolute_url())
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_comment_create_view(
    myselenium, axe_class, axe_options, login_method, helpdesk_testdata, live_server
):
    gamer = helpdesk_testdata.gamer1
    login_method(myselenium, gamer.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "helpdesk:issue-add-comment",
            kwargs={"ext_id": helpdesk_testdata.issue1.external_id},
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.parametrize(
    "view_name", ["helpdesk:issue-edit-comment", "helpdesk:issue-delete-comment"]
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_comment_edit_views(
    myselenium,
    axe_class,
    axe_options,
    login_method,
    helpdesk_testdata,
    live_server,
    view_name,
):
    gamer = helpdesk_testdata.gamer1
    login_method(myselenium, gamer.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            view_name,
            kwargs={
                "ext_id": helpdesk_testdata.issue1.external_id,
                "cext_id": helpdesk_testdata.comment1.external_id,
            },
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)
