import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

from .. import models

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "max_queries, url_to_test, gamer_to_use, expected_count, expected_response_code, expected_location",
    [
        (50, reverse("game_catalog:pub-list"), None, 2, 200, None),
        (50, reverse("game_catalog:system-list"), None, 2, 200, None),
        (50, reverse("game_catalog:game-list"), None, 3, 200, None),
        (50, reverse("game_catalog:module-list"), None, 3, 200, None),
        (50, reverse("game_catalog:correction_list"), "editor", 1, 200, None),
        (50, reverse("game_catalog:correction_list"), "random_gamer", None, 403, None),
        (
            50,
            reverse("game_catalog:correction_list"),
            None,
            None,
            302,
            "/accounts/login/",
        ),
        (
            50,
            reverse("game_catalog:addition_list"),
            None,
            None,
            302,
            "/accounts/login/",
        ),
        (50, reverse("game_catalog:addition_list"), "random_gamer", None, 403, None),
        (50, reverse("game_catalog:addition_list"), "editor", 1, 200, None),
        (150, reverse("game_catalog:recent_additions"), None, None, 200, None),
    ],
)
def test_list_views(
    client,
    catalog_testdata,
    django_assert_max_num_queries,
    max_queries,
    url_to_test,
    gamer_to_use,
    expected_count,
    expected_response_code,
    expected_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(max_queries):
        response = client.get(url_to_test)
    assert response.status_code == expected_response_code
    if expected_response_code == 200 and expected_count:
        assert len(response.context["object_list"]) == expected_count
    if expected_response_code == 302:
        assert expected_location in response["Location"]


@pytest.mark.parametrize(
    "view_name, gamer_to_use, object_name, url_kwarg, obj_attr, expected_response_code, expected_location",
    [
        ("game_catalog:pub-detail", None, "mcg", "publisher", "slug", 200, None),
        ("game_catalog:system-detail", None, "cypher", "system", "slug", 200, None),
        ("game_catalog:game-detail", None, "numensource", "game", "slug", 200, None),
        ("game_catalog:module-detail", None, "cos", "module", "slug", 200, None),
        ("game_catalog:edition_detail", None, "numen", "edition", "slug", 200, None),
        (
            "game_catalog:sourcebook_detail",
            None,
            "numenbook",
            "book",
            "slug",
            200,
            None,
        ),
        (
            "game_catalog:correction_detail",
            None,
            "correction1",
            "correction",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:addition_detail",
            None,
            "addition1",
            "addition",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:correction_detail",
            "random_gamer",
            "correction1",
            "correction",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:correction_detail",
            "editor",
            "correction1",
            "correction",
            "slug",
            200,
            None,
        ),
        (
            "game_catalog:addition_detail",
            "random_gamer",
            "addition1",
            "addition",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:addition_detail",
            "editor",
            "addition1",
            "addition",
            "slug",
            200,
            None,
        ),
    ],
)
def test_detail_view(
    client,
    catalog_testdata,
    django_assert_max_num_queries,
    view_name,
    gamer_to_use,
    object_name,
    url_kwarg,
    obj_attr,
    expected_response_code,
    expected_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                view_name,
                kwargs={
                    url_kwarg: getattr(getattr(catalog_testdata, object_name), obj_attr)
                },
            )
        )
    assert response.status_code == expected_response_code
    if expected_response_code == 302:
        assert expected_location in response["Location"]


@pytest.mark.parametrize(
    "view_name, gamer_to_use, model, expected_get_status_code, expected_get_location, post_data",
    [
        ("pub-create", None, models.GamePublisher, 302, "/accounts/login/", None),
        ("pub-create", "random_gamer", models.GamePublisher, 403, None, None),
        (
            "pub-create",
            "editor",
            models.GamePublisher,
            200,
            None,
            {"name": "Andrlik Publishing", "url": "https://www.andrlik.org"},
        ),
        ("game-create", None, models.PublishedGame, 302, "/accounts/login/", None),
        ("game-create", "random_gamer", models.PublishedGame, 403, None, None),
        (
            "game-create",
            "editor",
            models.PublishedGame,
            200,
            None,
            {
                "title": "Invisible Sun",
                "description": "So strange and surreal",
                "publication_date": "2017-10-01",
                "tags": "surreal, modern, fantasy",
            },
        ),
        ("system-create", None, models.GameSystem, 302, "/accounts/login/", None),
        ("system-create", "random_gamer", models.GameSystem, 403, None, None),
        ("system-create", "editor", models.GameSystem, 200, None, None),
    ],
)
def test_create_simple_views(
    client,
    catalog_testdata,
    view_name,
    gamer_to_use,
    model,
    expected_get_status_code,
    expected_get_location,
    post_data,
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    url = reverse("game_catalog:{}".format(view_name))
    response = client.get(url)
    assert response.status_code == expected_get_status_code
    if expected_get_status_code == 302 and expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_status_code == 200 and post_data:
        prev_count = model.objects.count()
        response = client.post(url, data=post_data)
        assert model.objects.count() - prev_count == 1


def test_create_system(client, catalog_testdata):
    client.force_login(user=catalog_testdata.editor.user)
    evilhat = models.GamePublisher.objects.create(name="Evil Hat Productions")
    sys_count = models.GameSystem.objects.count()
    response = client.post(
        reverse("game_catalog:system-create"),
        data={
            "name": "Forged in the dark",
            "original_publisher": evilhat.pk,
            "description": "I am here",
            "publication_date": "2016-09-01",
            "isbn": "",
            "system_url": "",
            "tags": "freeform, narrative",
        },
    )
    assert response.status_code == 302
    assert models.GameSystem.objects.count() - sys_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [
        (None, 302, "/accounts/login/"),
        ("random_gamer", 403, None),
        ("editor", 200, None),
    ],
)
def test_create_edition(
    client, catalog_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    url = reverse(
        "game_catalog:edition_create",
        kwargs={"game": catalog_testdata.numensource.slug},
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        edi_count = models.GameEdition.objects.count()
        response = client.post(
            url,
            data={
                "game_system": catalog_testdata.cypher.pk,
                "name": "Discovery and Destiny",
                "description": "A rewrite and expansion of the core rules adding community building.",
                "release_date": "2018-09-01",
                "tags": "community building, destiny",
                "publisher": catalog_testdata.mcg.pk,
            },
        )
        assert response.status_code == 302
        assert models.GameEdition.objects.count() - edi_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [
        (None, 302, "/accounts/login/"),
        ("random_gamer", 403, None),
        ("editor", 200, None),
    ],
)
def test_create_module(
    client, catalog_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    url = reverse(
        "game_catalog:module-create", kwargs={"edition": catalog_testdata.strange.slug}
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        prev_count = models.PublishedModule.objects.count()
        response = client.post(
            url,
            data={
                "title": "The Dark Spiral",
                "publisher": catalog_testdata.mcg.pk,
                "publication_date": "2013-10-15",
                "tags": "world hopping, advanced",
                "isbn": "",
            },
        )
        assert response.status_code == 302
        assert models.PublishedModule.objects.count() - prev_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [
        (None, 302, "/accounts/login/"),
        ("random_gamer", 403, None),
        ("editor", 200, None),
    ],
)
def test_create_sourcebook(
    client, catalog_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    url = reverse(
        "game_catalog:sourcebook_create",
        kwargs={"edition": catalog_testdata.numen.slug},
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if response.status_code == 200:
        prev_count = models.SourceBook.objects.count()
        response = client.post(
            url,
            data={
                "title": "Numenera",
                "publisher": catalog_testdata.mcg.pk,
                "corebook": 1,
                "release_date": "2012-07-01",
                "tags": "artwork",
            },
        )
        assert response.status_code == 302
        assert models.SourceBook.objects.count() - prev_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [(None, 302, "/accounts/login/"), ("random_gamer", 200, None)],
)
def test_create_correction(
    client, catalog_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    url = reverse(
        "game_catalog:correction_create",
        kwargs={"objtype": "edition", "object_id": catalog_testdata.numen.pk},
    )
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        prev_count = models.SuggestedCorrection.objects.count()
        response = client.post(
            url,
            data={
                "new_title": "Future monkeys are us",
                "new_url": "https://www.google.com",
                "new_description": "I ate something and now I feel bad.",
            },
        )
        assert response.status_code == 302
        assert models.SuggestedCorrection.objects.count() - prev_count == 1


def test_mismatched_correction_url(client, catalog_testdata):
    client.force_login(user=catalog_testdata.random_gamer.user)
    response = client.get(
        reverse(
            "game_catalog:correction_create",
            kwargs={"objtype": "sourcebook", "object_id": catalog_testdata.numen.pk},
        )
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_get_location",
    [(None, 302, "/accounts/login/"), ("random_gamer", 200, None)],
)
def test_addition_create(
    client, catalog_testdata, gamer_to_use, expected_get_response, expected_get_location
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    url = reverse("game_catalog:addition_create", kwargs={"obj_type": "edition"})
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]
    if expected_get_response == 200:
        prev_count = models.SuggestedAddition.objects.count()
        response = client.post(
            url,
            data={
                "title": "Future monkeys are us",
                "publisher": catalog_testdata.mcg.pk,
                "system": catalog_testdata.cypher.pk,
                "game": catalog_testdata.numensource.pk,
                "description": "I ate something and now I feel bad.",
            },
        )
        assert response.status_code == 302
        assert models.SuggestedAddition.objects.count() - prev_count == 1


@pytest.mark.parametrize(
    "view_name, gamer_to_use, object_name, object_kwarg, object_attr, expected_get_response, expected_get_location",
    [
        (
            "game_catalog:pub-edit",
            None,
            "mcg",
            "publisher",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:system-edit",
            None,
            "cypher",
            "system",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:game-edit",
            None,
            "numensource",
            "game",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:edition_edit",
            None,
            "numen",
            "edition",
            "slug",
            302,
            "/accounts/login",
        ),
        (
            "game_catalog:sourcebook_edit",
            None,
            "numenbook",
            "book",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:module-edit",
            None,
            "cos",
            "module",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:addition_update",
            None,
            "addition1",
            "addition",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:correction_update",
            None,
            "correction1",
            "correction",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:pub-delete",
            None,
            "mcg",
            "publisher",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:system-delete",
            None,
            "cypher",
            "system",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:game-delete",
            None,
            "numensource",
            "game",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:edition_delete",
            None,
            "numen",
            "edition",
            "slug",
            302,
            "/accounts/login",
        ),
        (
            "game_catalog:sourcebook_delete",
            None,
            "numenbook",
            "book",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:module-delete",
            None,
            "cos",
            "module",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:addition_delete",
            None,
            "addition1",
            "addition",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:correction_delete",
            None,
            "correction1",
            "correction",
            "slug",
            302,
            "/accounts/login/",
        ),
        (
            "game_catalog:pub-edit",
            "random_gamer",
            "mcg",
            "publisher",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:system-edit",
            "random_gamer",
            "cypher",
            "system",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:game-edit",
            "random_gamer",
            "numensource",
            "game",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:edition_edit",
            "random_gamer",
            "numen",
            "edition",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:sourcebook_edit",
            "random_gamer",
            "numenbook",
            "book",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:module-edit",
            "random_gamer",
            "cos",
            "module",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:addition_update",
            "random_gamer",
            "addition1",
            "addition",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:correction_update",
            "random_gamer",
            "correction1",
            "correction",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:pub-delete",
            "random_gamer",
            "mcg",
            "publisher",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:system-delete",
            "random_gamer",
            "cypher",
            "system",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:game-delete",
            "random_gamer",
            "numensource",
            "game",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:edition_delete",
            "random_gamer",
            "numen",
            "edition",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:sourcebook_delete",
            "random_gamer",
            "numenbook",
            "book",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:module-delete",
            "random_gamer",
            "cos",
            "module",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:addition_delete",
            "random_gamer",
            "addition1",
            "addition",
            "slug",
            403,
            None,
        ),
        (
            "game_catalog:correction_delete",
            "random_gamer",
            "correction1",
            "correction",
            "slug",
            403,
            None,
        ),
        ("game_catalog:pub-edit", "editor", "mcg", "publisher", "slug", 200, None),
        ("game_catalog:system-edit", "editor", "cypher", "system", "slug", 200, None),
        ("game_catalog:game-edit", "editor", "numensource", "game", "slug", 200, None),
        ("game_catalog:edition_edit", "editor", "numen", "edition", "slug", 200, None),
        (
            "game_catalog:sourcebook_edit",
            "editor",
            "numenbook",
            "book",
            "slug",
            200,
            None,
        ),
        ("game_catalog:module-edit", "editor", "cos", "module", "slug", 200, None),
        (
            "game_catalog:addition_update",
            "editor",
            "addition1",
            "addition",
            "slug",
            200,
            None,
        ),
        (
            "game_catalog:correction_update",
            "editor",
            "correction1",
            "correction",
            "slug",
            200,
            None,
        ),
        ("game_catalog:pub-delete", "editor", "mcg", "publisher", "slug", 200, None),
        ("game_catalog:system-delete", "editor", "cypher", "system", "slug", 200, None),
        (
            "game_catalog:game-delete",
            "editor",
            "numensource",
            "game",
            "slug",
            200,
            None,
        ),
        (
            "game_catalog:edition_delete",
            "editor",
            "numen",
            "edition",
            "slug",
            200,
            None,
        ),
        (
            "game_catalog:sourcebook_delete",
            "editor",
            "numenbook",
            "book",
            "slug",
            200,
            None,
        ),
        ("game_catalog:module-delete", "editor", "cos", "module", "slug", 200, None),
        (
            "game_catalog:addition_delete",
            "editor",
            "addition1",
            "addition",
            "slug",
            200,
            None,
        ),
        (
            "game_catalog:correction_delete",
            "editor",
            "correction1",
            "correction",
            "slug",
            200,
            None,
        ),
    ],
)
def test_load_edit_delete_views(
    client,
    catalog_testdata,
    view_name,
    gamer_to_use,
    object_name,
    object_kwarg,
    object_attr,
    expected_get_response,
    expected_get_location,
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    obj = getattr(catalog_testdata, object_name)
    url = reverse(view_name, kwargs={object_kwarg: getattr(obj, object_attr)})
    response = client.get(url)
    assert response.status_code == expected_get_response
    if expected_get_location:
        assert expected_get_location in response["Location"]


@pytest.mark.parametrize(
    "view_name, object_name, object_attr, object_kwarg",
    [
        ("game_catalog:pub-delete", "mcg", "slug", "publisher"),
        ("game_catalog:system-delete", "cypher", "slug", "system"),
        ("game_catalog:game-delete", "numensource", "slug", "game"),
        ("game_catalog:edition_delete", "numen", "slug", "edition"),
        ("game_catalog:sourcebook_delete", "numenbook", "slug", "book"),
        ("game_catalog:correction_delete", "correction1", "slug", "correction"),
        ("game_catalog:addition_delete", "addition1", "slug", "addition"),
    ],
)
def test_delete_views(
    client, catalog_testdata, view_name, object_name, object_attr, object_kwarg
):
    client.force_login(user=catalog_testdata.editor.user)
    obj = getattr(catalog_testdata, object_name)
    model = type(obj)
    response = client.post(
        reverse(view_name, kwargs={object_kwarg: getattr(obj, object_attr)})
    )
    assert response.status_code == 302
    with pytest.raises(ObjectDoesNotExist):
        model.objects.get(pk=obj.pk)


@pytest.mark.parametrize(
    "view_name, object_name, object_kwarg",
    [
        ("game_catalog:correction_review", "correction1", "correction"),
        ("game_catalog:addition_review", "addition1", "addition"),
    ],
)
def test_addition_correction_post_required(
    client, catalog_testdata, view_name, object_name, object_kwarg
):
    client.force_login(user=catalog_testdata.editor.user)
    response = client.get(
        reverse(
            view_name,
            kwargs={object_kwarg: getattr(catalog_testdata, object_name).slug},
        )
    )
    assert response.status_code == 405


@pytest.mark.parametrize(
    "view_name, gamer_to_use, object_name, object_kwarg, submit_status, expected_response_status, expected_obj_status",
    [
        (
            "game_catalog:correction_review",
            None,
            "correction1",
            "correction",
            "approve",
            302,
            "new",
        ),
        (
            "game_catalog:correction_review",
            "random_gamer",
            "correction1",
            "correction",
            "approve",
            403,
            "new",
        ),
        (
            "game_catalog:correction_review",
            "editor",
            "correction1",
            "correction",
            "approve",
            302,
            "approved",
        ),
        (
            "game_catalog:correction_review",
            "editor",
            "correction1",
            "correction",
            "reject",
            302,
            "rejected",
        ),
        (
            "game_catalog:addition_review",
            None,
            "addition1",
            "addition",
            "approve",
            302,
            "new",
        ),
        (
            "game_catalog:addition_review",
            "random_gamer",
            "addition1",
            "addition",
            "approve",
            403,
            "new",
        ),
        (
            "game_catalog:addition_review",
            "editor",
            "addition1",
            "addition",
            "approve",
            302,
            "approved",
        ),
        (
            "game_catalog:addition_review",
            "editor",
            "addition1",
            "addition",
            "reject",
            302,
            "rejected",
        ),
    ],
)
def test_addition_correction_approve_reject(
    client,
    catalog_testdata,
    view_name,
    gamer_to_use,
    object_name,
    object_kwarg,
    submit_status,
    expected_response_status,
    expected_obj_status,
):
    if gamer_to_use:
        client.force_login(user=getattr(catalog_testdata, gamer_to_use).user)
    obj = getattr(catalog_testdata, object_name)
    response = client.post(
        reverse(view_name, kwargs={object_kwarg: obj.slug}), data={submit_status: 1}
    )
    assert response.status_code == expected_response_status
    new_obj = type(obj).objects.get(pk=obj.pk)
    assert new_obj.status == expected_obj_status
    if expected_obj_status == "approved":
        if isinstance(new_obj, models.SuggestedCorrection):
            assert new_obj.new_title == new_obj.content_object.name
        else:
            assert models.GameEdition.objects.latest("created").name == "Numenera 4"


def test_publisher_update(client, catalog_testdata):
    post_data = {
        "name": "Monte Cook Games 2000",
        "url": "https://www.montecookgames.com",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:pub-edit", kwargs={"publisher": catalog_testdata.mcg.slug}
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert (
        models.GamePublisher.objects.get(pk=catalog_testdata.mcg.pk).name
        == "Monte Cook Games 2000"
    )


def test_game_update(client, catalog_testdata):
    post_data = {
        "title": "DND",
        "description": "Oh baby I like your way.",
        "publication_date": "1970-01-01",
        "tags": "crunchy, fantasy",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse("game_catalog:game-edit", kwargs={"game": catalog_testdata.dd.slug}),
        data=post_data,
    )
    assert response.status_code == 302
    assert models.PublishedGame.objects.get(pk=catalog_testdata.dd.pk).title == "DND"


def test_system_update(client, catalog_testdata):
    post_data = {
        "name": "Cypher System Reloaded",
        "original_publisher": catalog_testdata.mcg.pk,
        "description": "So much fun",
        "publication_date": "2012-07-01",
        "isbn": "",
        "system_url": "",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:system-edit", kwargs={"system": catalog_testdata.cypher.slug}
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert (
        models.GameSystem.objects.get(pk=catalog_testdata.cypher.pk).name
        == "Cypher System Reloaded"
    )


def test_edition_update(client, catalog_testdata):
    post_data = {
        "game_system": catalog_testdata.cypher.pk,
        "name": "OG",
        "description": "Explore the Ninth World",
        "publisher": catalog_testdata.mcg.pk,
        "release_date": "2012-07-01",
        "tags": "discovery",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:edition_edit", kwargs={"edition": catalog_testdata.numen.slug}
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert models.GameEdition.objects.get(pk=catalog_testdata.numen.pk).name == "OG"


def test_sourcebook_update(client, catalog_testdata):
    post_data = {
        "title": "Numenera OG",
        "publisher": catalog_testdata.mcg.pk,
        "corebook": 1,
        "release_date": "2012-07-01",
        "tags": "artwork",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:sourcebook_edit",
            kwargs={"book": catalog_testdata.numenbook.slug},
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert (
        models.SourceBook.objects.get(pk=catalog_testdata.numenbook.pk).title
        == "Numenera OG"
    )


def test_module_update(client, catalog_testdata):
    post_data = {
        "title": "RAVENLOFT!!!!",
        "publisher": catalog_testdata.wotc.pk,
        "publication_date": "2016-11-01",
        "tags": "horror, nonlinear",
        "isbn": "",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:module-edit", kwargs={"module": catalog_testdata.cos.slug}
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert (
        models.PublishedModule.objects.get(pk=catalog_testdata.cos.pk).title
        == "RAVENLOFT!!!!"
    )


def test_correction_update(client, catalog_testdata):
    post_data = {
        "new_title": "Future monkeys are us",
        "new_url": "https://www.google.com",
        "new_description": "I ate something and now I feel bad.",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:correction_update",
            kwargs={"correction": catalog_testdata.correction1.slug},
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert (
        models.SuggestedCorrection.objects.get(
            pk=catalog_testdata.correction1.pk
        ).new_title
        == "Future monkeys are us"
    )


def test_addition_update(client, catalog_testdata):
    post_data = {
        "title": "Future monkeys are us",
        "publisher": catalog_testdata.mcg.pk,
        "system": catalog_testdata.cypher.pk,
        "game": catalog_testdata.numensource.pk,
        "description": "I ate something and now I feel bad.",
    }
    client.force_login(user=catalog_testdata.editor.user)
    response = client.post(
        reverse(
            "game_catalog:addition_update",
            kwargs={"addition": catalog_testdata.addition1.slug},
        ),
        data=post_data,
    )
    assert response.status_code == 302
    assert (
        models.SuggestedAddition.objects.get(pk=catalog_testdata.addition1.pk).title
        == "Future monkeys are us"
    )
