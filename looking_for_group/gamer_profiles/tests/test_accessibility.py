import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    "url_to_check",
    [
        reverse("gamer_profiles:community-list"),
        reverse("gamer_profiles:my-community-list"),
        reverse("gamer_profiles:my-application-list"),
        reverse("gamer_profiles:community-create"),
        reverse("gamer_profiles:my-gamer-friend-requests"),
        reverse("gamer_profiles:my-block-list"),
        reverse("gamer_profiles:profile-edit"),
        "myprofile",
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_list_views(
    myselenium,
    axe_class,
    axe_options,
    live_server,
    login_method,
    social_gamer_to_check,
    url_to_check,
):
    login_method(myselenium, social_gamer_to_check.user, live_server)
    if url_to_check == "myprofile":
        url_to_check = social_gamer_to_check.get_absolute_url()
    myselenium.get(live_server.url + url_to_check)
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.parametrize(
    "view_name",
    [
        "gamer_profiles:community-edit",
        "gamer_profiles:community-detail",
        "gamer_profiles:community-delete",
        "gamer_profiles:community-member-list",
    ],
)
@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_community_edit(
    myselenium,
    axe_class,
    axe_options,
    live_server,
    login_method,
    social_gamer_to_check,
    social_community_slug,
    view_name,
):
    login_method(myselenium, social_gamer_to_check.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(view_name, kwargs={"community": social_community_slug})
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)


@pytest.mark.accessibility
@pytest.mark.nondestructive
def test_add_gamer_note(
    myselenium,
    axe_class,
    axe_options,
    live_server,
    login_method,
    social_gamer_to_check,
    social_testdata,
):
    login_method(myselenium, social_gamer_to_check.user, live_server)
    myselenium.get(
        live_server.url
        + reverse(
            "gamer_profiles:add-gamer-note",
            kwargs={"gamer": social_testdata.gamer3.username},
        )
    )
    axe = axe_class(myselenium)
    violations = axe.get_axe_results(options=axe_options)["violations"]
    assert len(violations) == 0, axe.report(violations)
