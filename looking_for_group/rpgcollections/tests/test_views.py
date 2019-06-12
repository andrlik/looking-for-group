import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.urls import reverse
from factory.django import mute_signals

from looking_for_group.rpgcollections import models

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "view_name, expected_status_code, gamer_to_use, expected_location",
    [
        (
            "rpgcollections:book-detail",
            302,
            None,
            "/accounts/login/",
        ),  # Non authenticated for book detail
        (
            "rpgcollections:book-detail",
            403,
            "gamer3",
            None,
        ),  # Authenticated, but not connected for book detail
        ("rpgcollections:book-detail", 200, "gamer2", None),  # Friend can view.
        ("rpgcollections:book-detail", 200, "gamer1", None),  # Owner can view
        (
            "rpgcollections:edit-book",
            302,
            None,
            "/accounts/login/",
        ),  # Non-authenticated user for edit book
        (
            "rpgcollections:edit-book",
            403,
            "gamer2",
            None,
        ),  # Only the owner should be able to edit
        ("rpgcollections:edit-book", 200, "gamer1", None),  # Owner can edit
        (
            "rpgcollections:remove-book",
            302,
            None,
            "/accounts/login/",
        ),  # Non authenticated redirects
        ("rpgcollections:remove-book", 403, "gamer2", None),  # Only owner can delete
        ("rpgcollections:remove-book", 200, "gamer1", None),  # Owner can delete
    ],
)
def test_get_requests_for_access(
    client,
    collection_testdata,
    django_assert_max_num_queries,
    view_name,
    expected_status_code,
    gamer_to_use,
    expected_location,
):
    """
    Test that making GET requests for the detail views results in the expected result.
    """
    if gamer_to_use:
        client.force_login(user=getattr(collection_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                view_name, kwargs={"book": collection_testdata.cypher_collect_1.slug}
            )
        )
    assert response.status_code == expected_status_code
    if expected_location:
        assert expected_location in response["Location"]


def test_update_book_data(client, collection_testdata):
    client.force_login(user=collection_testdata.gamer1.user)
    with mute_signals(post_save):
        response = client.post(
            reverse(
                "rpgcollections:edit-book",
                kwargs={"book": collection_testdata.cypher_collect_1.slug},
            ),
            data={
                "object_id": collection_testdata.cypher_collect_1.content_object.pk,
                "in_print": 1,
                "in_pdf": 1,
            },
        )
    assert response.status_code == 302
    tmpchk = models.Book.objects.get(pk=collection_testdata.cypher_collect_1.pk)
    assert tmpchk.in_print and tmpchk.in_pdf


def test_delete_book(client, collection_testdata):
    client.force_login(user=collection_testdata.gamer1.user)
    col_count = models.Book.objects.filter(
        library=collection_testdata.game_lib1
    ).count()
    with mute_signals(post_delete):
        client.post(
            reverse(
                "rpgcollections:remove-book",
                kwargs={"book": collection_testdata.cypher_collect_1.slug},
            ),
            data={},
        )
    assert (
        col_count
        - models.Book.objects.filter(library=collection_testdata.game_lib1).count()
        == 1
    )
    with pytest.raises(ObjectDoesNotExist):
        models.Book.objects.get(pk=collection_testdata.cypher_collect_1.pk)


def test_post_required_for_add(client, collection_testdata):
    client.force_login(user=collection_testdata.gamer2.user)
    response = client.get(
        reverse("rpgcollections:add-book", kwargs={"booktype": "system"})
    )
    assert response.status_code == 405


@pytest.mark.parametrize(
    "gamer_to_use, data, expected_status_code, expected_collection_count_diff",
    [
        ("gamer2", "good", 302, 1),  # Valid add for a user that doesn't have it yet.
        (
            "gamer1",
            "good",
            302,
            0,
        ),  # Trying to add when already there should have no effect
        ("gamer2", "bad", 302, 0),  # Using bad data should not add to the library
    ],
)
def test_add_book(
    client,
    collection_testdata,
    gamer_to_use,
    data,
    expected_status_code,
    expected_collection_count_diff,
):
    data_dict = {
        "good": {"object_id": collection_testdata.cypher.pk, "in_print": 1},
        "bad": {"object_id": collection_testdata.cypher.pk},
    }
    gamer = getattr(collection_testdata, gamer_to_use)
    client.force_login(user=gamer.user)
    game_lib = models.GameLibrary.objects.get(user=gamer.user)
    col_count = models.Book.objects.filter(library=game_lib).count()
    with mute_signals(post_save):
        response = client.post(
            reverse("rpgcollections:add-book", kwargs={"booktype": "system"}),
            data=data_dict[data],
        )
    assert response.status_code == expected_status_code
    assert (
        models.Book.objects.filter(library=game_lib).count() - col_count
        == expected_collection_count_diff
    )
