import urllib
from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_delete
from django.urls import reverse
from django.utils import timezone
from factory.django import mute_signals

from ...invites.models import Invite
from .. import models
from ..utils import mkfirstOfmonth, mkLastOfMonth

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_result_count",
    [
        (None, 302, None),
        ("gamer1", 200, 2),
        ("gamer2", 200, 1),
        ("gamer3", 200, 3),
        ("gamer4", 200, 3),
    ],
)
def test_game_posting_list(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_result_count,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse("games:game_list"))
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        assert len(response.context["game_list"]) == expected_result_count


@pytest.mark.parametrize(
    "gamer_to_use, expected_active, expected_past",
    [(None, None, None), ("gamer4", 3, 1)],
)
def test_my_game_list(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_active,
    expected_past,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse("games:my_game_list"))
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 200
        assert len(response.context["active_game_list"]) == expected_active
        assert len(response.context["completed_game_list"]) == expected_past


@pytest.mark.parametrize(
    "gamer_to_use, expected_post_response",
    [(None, 302), ("gamer2", 200), ("gamer1", 302)],
)
def test_game_create_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_post_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    url = reverse("games:game_create")
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 200
    prev_count = models.GamePosting.objects.count()
    response = client.post(
        url,
        data={
            "title": "A Valid Campaign",
            "status": "open",
            "game_type": "campaign",
            "privacy_level": "community",
            "min_players": 1,
            "max_players": 3,
            "game_description": "We like pie.",
            "session_length": 2.5,
            "game_frequency": "weekly",
            "communities": [game_testdata.comm1.pk],
        },
    )
    if not gamer_to_use:
        assert assert_login_redirect(response)
        assert models.GamePosting.objects.count() == prev_count
    else:
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert models.GamePosting.objects.count() - prev_count == 1


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer1", 200), ("gamer2", 302)],
)
def test_game_detail_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(200):
        response = client.get(
            reverse("games:game_detail", kwargs={"gameid": game_testdata.gp2.slug})
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        if expected_get_response == 302:
            assert "apply" in response["Location"]


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, post_data_key, expected_post_response",
    [
        (None, 302, None, None),
        ("gamer2", 403, "valid", 403),
        ("gamer1", 200, "invalid", 200),
        ("gamer1", 200, "valid", 302),
    ],
)
def test_game_update_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    post_data_key,
    expected_post_response,
):
    post_data_dict = {
        "invalid": {
            "title": "A Valid Campaign",
            "game_type": "campaign",
            "status": "open",
            "privacy_level": "community",
            "min_players": 1,
            "max_players": 3,
            "game_description": "I ate a whole pie once.",
            "session_length": 2.5,
            "game_frequency": "weekly",
            "communities": [game_testdata.comm2.pk],
        },
        "valid": {
            "title": "A Valid Campaign",
            "game_type": "campaign",
            "status": "open",
            "privacy_level": "community",
            "min_players": 1,
            "max_players": 3,
            "game_description": "Some of us enjoy cake, too.",
            "session_length": 2.5,
            "game_frequency": "weekly",
            "communities": [game_testdata.comm1.pk],
        },
    }
    url = reverse("games:game_edit", kwargs={"gameid": game_testdata.gp2.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        with mute_signals(post_save):
            response = client.post(url, data=post_data_dict[post_data_key])
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.GamePosting.objects.get(id=game_testdata.gp2.id).title
                == "A Valid Campaign"
            )
        else:
            assert (
                models.GamePosting.objects.get(id=game_testdata.gp2.id).title
                == game_testdata.gp2.title
            )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [(None, 302, None), ("gamer2", 403, 403), ("gamer4", 200, 302)],
)
def test_game_delete_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse("games:game_delete", kwargs={"gameid": game_testdata.gp4.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.GamePosting.objects.get(id=game_testdata.gp4.id)
        else:
            assert models.GamePosting.objects.get(id=game_testdata.gp4.id)


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, should_submit, expected_post_response",
    [
        (None, 302, False, None),  # Login required
        ("blocked_gamer", 403, False, 403),  # Gamer is blocked by GM
        ("gamer1", 302, False, None),  # GM
        ("gamer4", 302, False, None),  # Existing player
        ("gamer2", 200, False, 302),  # Valid applicant w/o submit
        ("gamer2", 200, True, 302),  # Valid applicant w/ submit
    ],
)
def test_game_apply_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    should_submit,
    expected_post_response,
):
    if gamer_to_use:
        gamer = getattr(game_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    url = reverse("games:game_apply", kwargs={"gameid": game_testdata.gp2.slug})
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert expected_get_response == response.status_code
        if expected_get_response != 302:
            post_data = {"message": "Thanks for your consideration!"}
            if should_submit:
                post_data["submit_app"] = ""
            previous_apps = models.GamePostingApplication.objects.count()
            response = client.post(url, data=post_data)
            assert response.status_code == expected_post_response
            if expected_post_response == 302:
                assert previous_apps < models.GamePostingApplication.objects.count()
                if should_submit:
                    assert (
                        models.GamePostingApplication.objects.filter(gamer=gamer)
                        .latest("created")
                        .status
                        == "pending"
                    )
                else:
                    assert (
                        models.GamePostingApplication.objects.filter(gamer=gamer)
                        .latest("created")
                        .status
                        == "new"
                    )
            else:
                assert previous_apps == models.GamePostingApplication.objects.count()


@pytest.mark.parametrize(
    "gamer_to_use, status_to_use, expected_get_response",
    [
        (None, "new", 302),  # Login required
        ("gamer3", "new", 403),  # Other gamer
        ("gamer1", "new", 403),  # GM before submit
        ("gamer2", "new", 200),  # Author
        ("gamer1", "pending", 200),  # GM after submit
    ],
)
def test_game_application_detail_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    status_to_use,
    expected_get_response,
):
    application = models.GamePostingApplication.objects.create(
        game=game_testdata.gp2,
        gamer=game_testdata.gamer2,
        message="hi",
        status=status_to_use,
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse("games:game_apply_detail", kwargs={"application": application.slug})
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, should_submit, expected_post_response",
    [
        (None, 302, False, None),  # Login required
        ("gamer3", 403, False, 403),  # Other gamer
        ("gamer1", 403, False, 403),  # GM
        ("gamer2", 200, False, 302),  # Valid w/o submit
        ("gamer2", 200, True, 302),  # Valid with submit
    ],
)
def test_game_application_update_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    should_submit,
    expected_post_response,
):
    application = models.GamePostingApplication.objects.create(
        game=game_testdata.gp2, gamer=game_testdata.gamer2, message="Hi", status="new"
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    url = reverse("games:game_apply_update", kwargs={"application": application.slug})
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        post_data = {"message": "I would like to play"}
        if should_submit:
            post_data["submit_app"] = ""
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            new_version = models.GamePostingApplication.objects.get(pk=application.pk)
            assert new_version.message == "I would like to play"
            if should_submit:
                assert new_version.status == "pending"
            else:
                assert new_version.status == "new"
        else:
            application.refresh_from_db()
            assert application.message == "Hi"
            assert application.status == "new"


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer3", 403, 403),  # Other user
        ("gamer1", 403, 403),  # GM
        ("gamer2", 200, 302),  # Valid author
    ],
)
def test_application_withdrawl_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    application = models.GamePostingApplication.objects.create(
        game=game_testdata.gp2, gamer=game_testdata.gamer2, message="Hi", status="new"
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    url = reverse("games:game_apply_delete", kwargs={"application": application.slug})
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.GamePostingApplication.objects.get(id=application.id)
        else:
            assert models.GamePostingApplication.objects.get(id=application.id)


@pytest.mark.parametrize("gamer_to_use", [(None), ("gamer4"), ("gamer2")])
def test_game_posting_applied_list(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
):
    """
    Test gamers list of games applied for.
    """
    models.GamePostingApplication.objects.create(
        game=game_testdata.gp2,
        gamer=game_testdata.gamer2,
        message="Hi",
        status="pending",
    )
    models.GamePostingApplication.objects.create(
        game=game_testdata.gp3,
        gamer=game_testdata.gamer4,
        message="Pick me!",
        status="new",
    )
    models.GamePostingApplication.objects.create(
        game=game_testdata.gp1,
        gamer=game_testdata.gamer3,
        message="Try again",
        status="deny",
    )
    models.GamePostingApplication.objects.create(
        game=game_testdata.gp2,
        gamer=game_testdata.gamer3,
        message="You up?",
        status="approve",
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(reverse("games:my-game-applications"))
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 200


@pytest.mark.parametrize(
    "gamer_to_use, post_data, expected_post_response",
    [
        (None, {"status": "approve"}, 302),
        ("gamer3", {"status": "approve"}, 403),
        ("gamer1", {"status": "approve"}, 302),
        ("gamer1", {"status": "deny"}, 302),
    ],
)
def test_application_approve_reject(
    client,
    game_testdata,
    assert_login_redirect,
    gamer_to_use,
    post_data,
    expected_post_response,
):
    application = models.GamePostingApplication.objects.create(
        game=game_testdata.gp2,
        gamer=game_testdata.gamer2,
        message="Hi",
        status="pending",
    )
    url = reverse(
        "games:game_application_approve_reject",
        kwargs={"application": application.slug},
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    response = client.get(url)
    assert response.status_code == 405
    with mute_signals(post_save):
        response = client.post(url, data=post_data)
    if not gamer_to_use:
        assert assert_login_redirect(response)
        assert (
            models.GamePostingApplication.objects.get(id=application.id).status
            == "pending"
        )
    else:
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.GamePostingApplication.objects.get(id=application.id).status
                == post_data["status"]
            )
            game_testdata.gp2.refresh_from_db()
            if post_data["status"] == "approve":
                assert game_testdata.gamer2 in game_testdata.gp2.players.all()
            else:
                assert game_testdata.gamer2 not in game_testdata.gp2.players.all()
        else:
            assert (
                models.GamePostingApplication.objects.get(id=application.id).status
                == "pending"
            )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer2", 403), ("gamer4", 200), ("gamer1", 200)],
)
def test_game_session_list_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse("games:session_list", kwargs={"gameid": game_testdata.gp2.slug})
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, game_closed, expected_get_response, expected_post_response, expected_post_increase",
    [
        (None, False, 302, None, None),  # Login required
        ("gamer2", False, 403, 403, 0),  # Outsider
        ("gamer4", False, 403, 403, 0),  # Player
        ("gamer1", True, 302, 302, 0),  # GM but game already closed
        ("gamer1", False, 200, 302, 1),  # GM Successful
    ],
)
def test_adhoc_session_create_test(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    game_closed,
    expected_get_response,
    expected_post_response,
    expected_post_increase,
):
    url = reverse(
        "games:session_adhoc_create", kwargs={"gameid": game_testdata.gp2.slug}
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    if game_closed:
        with mute_signals(post_save):
            game_testdata.session2.status = "complete"
            game_testdata.session2.save()
            game_testdata.gp2.status = "closed"
            game_testdata.gp2.save()
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        previous_count = models.GameSession.objects.filter(
            game=game_testdata.gp2
        ).count()
        with mute_signals(post_save):
            response = client.post(
                url,
                data={
                    "scheduled_time": (timezone.now() + timedelta(days=1)).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "players_expected": [
                        f.pk
                        for f in models.Player.objects.filter(game=game_testdata.gp2)
                    ],
                    "players_missing": [],
                    "gm_notes": "",
                },
            )
        assert response.status_code == expected_post_response
        assert (
            models.GameSession.objects.filter(game=game_testdata.gp2).count()
            - previous_count
            == expected_post_increase
        )


@pytest.mark.parametrize(
    "gamer_to_use, prev_session_closed, game_closed, expected_post_response, expected_post_increase",
    [
        (None, True, False, 302, 0),  # Login required
        ("gamer2", True, False, 403, 0),  # Outsider
        ("gamer4", True, False, 403, 0),  # Player
        ("gamer1", False, False, 302, 0),  # Still an open session.
        ("gamer1", True, True, 302, 0),  # Game is done, can't add a session.
        (
            "gamer1",
            True,
            False,
            302,
            1,
        ),  # Previous session completed and active game. Success!
    ],
)
def test_session_create_view(
    client,
    game_testdata,
    assert_login_redirect,
    gamer_to_use,
    prev_session_closed,
    game_closed,
    expected_post_response,
    expected_post_increase,
):
    url = reverse("games:session_create", kwargs={"gameid": game_testdata.gp2.slug})
    with mute_signals(post_save):
        if prev_session_closed:
            game_testdata.session2.status = "complete"
            game_testdata.session2.save()
        if game_closed:
            game_testdata.gp2.status = "closed"
            game_testdata.gp2.save()
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == 405  # POST required
    prev_session_count = models.GameSession.objects.filter(
        game=game_testdata.gp2
    ).count()
    with mute_signals(post_save):
        response = client.post(url, data={"game": game_testdata.gp2.pk})
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_post_response
    assert (
        models.GameSession.objects.filter(game=game_testdata.gp2).count()
        - prev_session_count
        == expected_post_increase
    )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [
        (None, 302),  # Login required
        ("gamer2", 403),  # Outsider
        ("gamer4", 200),  # Player
        ("gamer1", 200),  # GM
    ],
)
def test_session_detail_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "games:session_detail", kwargs={"session": game_testdata.session1.slug}
            )
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Outsider
        ("gamer4", 403, 403),  # Player
        ("gamer1", 200, 302),  # GM
    ],
)
def test_session_update_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    post_data = {
        "players_expected": [
            f.pk for f in models.Player.objects.filter(game=game_testdata.gp2)
        ],
        "players_missing": [],
        "gm_notes": "This will be wild and **wacky**!",
    }
    url = reverse("games:session_edit", kwargs={"session": game_testdata.session2.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        with mute_signals(post_save):
            response = client.post(url, data=post_data)
            assert response.status_code == expected_post_response
            if expected_post_response == 302:
                assert (
                    models.GameSession.objects.get(
                        id=game_testdata.session2.id
                    ).gm_notes
                    == post_data["gm_notes"]
                )
            else:
                assert not (
                    models.GameSession.objects.get(
                        id=game_testdata.session2.id
                    ).gm_notes
                )


@pytest.mark.parametrize(
    "viewname, toggletype, gamer_to_use, expected_post_response, should_update",
    [
        (
            "games:session_complete_toggle",
            "complete",
            None,
            302,
            False,
        ),  # Login required
        ("games:session_cancel", "cancel", None, 302, False),  # Login required
        ("games:session_uncancel", "pending", None, 302, False),  # Login required
        ("games:session_complete_toggle", "complete", "gamer2", 403, False),  # Outsider
        ("games:session_cancel", "cancel", "gamer2", 403, False),  # Outsider
        ("games:session_uncancel", "pending", "gamer2", 403, False),  # Outsider
        ("games:session_complete_toggle", "complete", "gamer4", 403, False),  # Player
        ("games:session_cancel", "cancel", "gamer4", 403, False),  # Player
        ("games:session_uncancel", "pending", "gamer4", 403, False),  # Player
        ("games:session_complete_toggle", "complete", "gamer1", 302, True),  # GM
        (
            "games:session_complete_toggle",
            "cancel",
            "gamer1",
            302,
            False,
        ),  # Invalid status option
        ("games:session_cancel", "cancel", "gamer1", 302, True),  # GM
        ("games:session_uncancel", "pending", "gamer1", 302, True),  # GM
    ],
)
def test_session_complete_cancel_toggles(
    client,
    game_testdata,
    assert_login_redirect,
    viewname,
    toggletype,
    gamer_to_use,
    expected_post_response,
    should_update,
):
    if viewname == "games:session_uncancel":
        with mute_signals(post_save):
            game_testdata.session2.cancel()
    url = reverse(viewname, kwargs={"session": game_testdata.session2.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    response = client.get(url)
    assert response.status_code == 405  # POST required
    with mute_signals(post_save):
        response = client.post(url, data={"status": toggletype})
    if not gamer_to_use:
        assert assert_login_redirect(response)
        if viewname == "games:session_uncancel":
            assert (
                models.GameSession.objects.get(id=game_testdata.session2.id).status
                == "cancel"
            )
        else:
            assert (
                models.GameSession.objects.get(id=game_testdata.session2.id).status
                == "pending"
            )
    else:
        assert response.status_code == expected_post_response
        if expected_post_response == 302 and should_update:
            assert (
                models.GameSession.objects.get(id=game_testdata.session2.id).status
                == toggletype
            )
            if toggletype == "cancel":
                assert models.GameSession.objects.get(
                    id=game_testdata.session2.id
                ).occurrence.cancelled
            if toggletype == "complete":
                with mute_signals(post_save):
                    response = client.post(url, data={"status": "pending"})
                assert response.status_code == 302
                assert (
                    models.GameSession.objects.get(id=game_testdata.session2.id).status
                    == "pending"
                )
            if viewname == "games:session_uncancel":
                assert not models.GameSession.objects.get(
                    id=game_testdata.session2.id
                ).occurrence.cancelled
        else:
            if viewname == "games:session_uncancel":
                assert (
                    models.GameSession.objects.get(id=game_testdata.session2.id).status
                    == "cancel"
                )
            else:
                assert (
                    models.GameSession.objects.get(id=game_testdata.session2.id).status
                    == "pending"
                )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Outsider
        ("gamer4", 403, 403),  # Player
        ("gamer1", 200, 302),  # GM
    ],
)
def test_session_move_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse("games:session_move", kwargs={"session": game_testdata.session2.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        orig_time = game_testdata.session2.scheduled_time
        with mute_signals(post_save):
            response = client.post(
                url,
                data={
                    "scheduled_time": (
                        game_testdata.session2.scheduled_time + timedelta(days=1)
                    ).strftime("%Y-%m-%d %H:%M")
                },
            )
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            updated_version = models.GameSession.objects.get(
                id=game_testdata.session2.id
            )
            assert orig_time < updated_version.scheduled_time
            assert updated_version.occurrence.start == updated_version.scheduled_time
        else:
            assert (
                orig_time
                == models.GameSession.objects.get(
                    id=game_testdata.session2.id
                ).scheduled_time
            )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Outsider
        ("gamer4", 200, 302),  # Player - valid
        ("gamer1", 200, 302),  # GM - Valid
    ],
)
def test_adventure_log_create(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse("games:log_create", kwargs={"session": game_testdata.session1.slug})
    if gamer_to_use:
        gamer = getattr(game_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        prev_count = models.AdventureLog.objects.count()
        response = client.post(
            url,
            data={
                "title": "Mystery in the deep",
                "body": "Our heroes encountered a lot of **stuff**.",
            },
        )
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert models.AdventureLog.objects.count() - prev_count == 1
            assert models.AdventureLog.objects.latest("created").initial_author == gamer
        else:
            assert models.AdventureLog.objects.count() == prev_count


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Outsider
        ("gamer4", 200, 302),  # Player - valid
        ("gamer1", 200, 302),  # GM - valid
    ],
)
def test_adventure_log_update(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse("games:log_edit", kwargs={"log": game_testdata.log1.slug})
    post_data = {
        "title": "Mystery in the deep",
        "body": "Our heroes fought an octopus!",
    }
    if gamer_to_use:
        gamer = getattr(game_testdata, gamer_to_use)
        client.force_login(user=gamer.user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            game_testdata.log1.refresh_from_db()
            assert game_testdata.log1.body == post_data["body"]
            assert game_testdata.log1.last_edited_by == gamer
        else:
            assert (
                models.AdventureLog.objects.get(id=game_testdata.log1.id).body
                == "Our heroes encountered a lot of **stuff**"
            )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Outsider
        ("gamer4", 403, 403),  # Player - cannot delete
        ("gamer1", 200, 302),  # GM Valid
    ],
)
def test_adventure_log_delete_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse("games:log_delete", kwargs={"log": game_testdata.log1.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.AdventureLog.objects.get(id=game_testdata.log1.id)
        else:
            assert models.AdventureLog.objects.get(id=game_testdata.log1.id)


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [
        (None, 302),  # Login required
        ("gamer2", 403),  # Only calendar owner can see
        ("gamer1", 200),  # Calendar owner
    ],
)
def test_calendar_detail_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    with mute_signals(post_save):
        game_testdata.gp2.start_time = timezone.now() + timedelta(days=5)
        game_testdata.gp2.session_length = 2.5
        game_testdata.gp2.game_frequency = "weekly"
        game_testdata.gp2.save()
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "games:calendar_detail", kwargs={"gamer": game_testdata.gamer1.username}
            )
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [
        (None, 302),  # Login required
        ("gamer2", 403),  # Only calendar owner can view
        ("gamer1", 200),  # Calendar ownder - valid
    ],
)
def test_calendar_json_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    query_values = {
        "calendar_slug": game_testdata.gamer1.username,
        "start": mkfirstOfmonth(timezone.now()).strftime("%Y-%m-%d"),
        "end": mkLastOfMonth(timezone.now()).strftime("%Y-%m-%d"),
        "timezone": timezone.now().strftime("%Z"),
    }
    query_string = urllib.parse.urlencode(query_values)
    url = "{}?{}".format(reverse("games:api_occurrences"), query_string)
    with mute_signals(post_save):
        game_testdata.gp2.start_time = timezone.now() + timedelta(days=5)
        game_testdata.gp2.session_length = 2.5
        game_testdata.gp2.game_frequency = "weekly"
        game_testdata.gp2.save()
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "view_name, gamer_to_use, expected_get_response, expected_post_response",
    [
        ("games:player_leave", None, 302, None),  # Login required
        ("games:player_leave", "gamer2", 403, 403),  # Outsider
        ("games:player_leave", "gamer4", 200, 302),  # PLayer that is leaving
        ("games:player_leave", "gamer1", 403, 403),  # GM - invalid for this function
        ("games:player_kick", None, 302, None),  # Login required
        ("games:player_kick", "gamer2", 403, 403),  # Outsider
        ("games:player_kick", "gamer4", 403, 403),  # PLayer can't kick themselves
        ("games:player_kick", "gamer1", 200, 302),  # GM - CAN KICK
    ],
)
def test_player_kick_leave(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    view_name,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse(
        view_name,
        kwargs={"gameid": game_testdata.gp2.slug, "player": game_testdata.player1.slug},
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        with mute_signals(pre_delete):
            response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.Player.objects.get(id=game_testdata.player1.id)
        else:
            assert models.Player.objects.get(id=game_testdata.player1.id)


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer4", 403, 403),  # Players can't create another player's character
        ("gamer1", 403, 403),  # GMs can't make a player character
        ("gamer3", 200, 302),  # Same as player -- valid
    ],
)
def test_character_create(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse(
        "games:character_create", kwargs={"player": game_testdata.player2.slug}
    )
    post_data = {"name": "Magic Brian", "description": "Elven wizard"}
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        prev_count = models.Character.objects.count()
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert models.Character.objects.count() - prev_count == 1
        else:
            assert models.Character.objects.count() == prev_count


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [
        (None, 302),  # Login required
        ("gamer2", 403),  # Not in the game
        ("gamer3", 200),  # In game
        ("gamer4", 200),  # Character owner
        ("gamer1", 200),  # GM
    ],
)
def test_character_detail_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "games:character_detail",
                kwargs={"character": game_testdata.character1.slug},
            )
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Not in game
        ("gamer3", 403, 403),  # Different player in same game
        ("gamer4", 200, 302),  # Character owner
        ("gamer1", 200, 302),  # GM
    ],
)
def test_character_update_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse(
        "games:character_edit", kwargs={"character": game_testdata.character1.slug}
    )
    post_data = {"name": "Magic Brian", "description": "Half-drow wizard"}
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data=post_data)
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.Character.objects.get(id=game_testdata.character1.id).description
                == post_data["description"]
            )
        else:
            assert (
                models.Character.objects.get(id=game_testdata.character1.id).description
                != post_data["description"]
            )


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response, expected_post_response",
    [
        (None, 302, None),  # Login required
        ("gamer2", 403, 403),  # Not in game
        ("gamer3", 403, 403),  # In game, but not owner
        ("gamer1", 403, 403),  # GM Can't delete a players character
        ("gamer4", 200, 302),  # Character owner
    ],
)
def test_character_delete_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
    expected_post_response,
):
    url = reverse(
        "games:character_delete", kwargs={"character": game_testdata.character1.slug}
    )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        response = client.post(url, data={})
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            with pytest.raises(ObjectDoesNotExist):
                models.Character.objects.get(id=game_testdata.character1.id)
        else:
            assert models.Character.objects.get(id=game_testdata.character1.id)


@pytest.mark.parametrize(
    "gamer_to_use, view_name, status_to_send, expected_post_response",
    [
        (None, "games:character_approve", "approved", 302),  # Login Required
        (None, "games:character_reject", "rejected", 302),  # Login required
        ("gamer2", "games:character_approve", "approved", 403),  # Not in game
        ("gamer2", "games:character_reject", "rejected", 403),  # Not in game
        ("gamer3", "games:character_approve", "approved", 403),  # Other player
        ("gamer3", "games:character_reject", "rejected", 403),  # Other player
        ("gamer4", "games:character_approve", "approved", 403),  # Character owner
        ("gamer4", "games:character_reject", "rejected", 403),  # Character owner
        ("gamer1", "games:character_approve", "approved", 302),  # GM
        ("gamer1", "games:character_reject", "rejected", 302),  # GM
    ],
)
def test_character_approve_reject(
    client,
    game_testdata,
    assert_login_redirect,
    gamer_to_use,
    view_name,
    status_to_send,
    expected_post_response,
):
    url = reverse(view_name, kwargs={"character": game_testdata.character1.slug})
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    response = client.get(url)
    assert response.status_code == 405
    response = client.post(url, data={"status": status_to_send})
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_post_response
        if expected_post_response == 302:
            assert (
                models.Character.objects.get(id=game_testdata.character1.id).status
                == status_to_send
            )
        else:
            assert (
                models.Character.objects.get(id=game_testdata.character1.id).status
                == "pending"
            )


@pytest.mark.parametrize(
    "gamer_to_use, view_name, status_to_send, expected_post_response",
    [
        (None, "games:character_inactivate", "inactive", 302),  # Login required
        (None, "games:character_reactivate", "pending", 302),  # Login required
        ("gamer2", "games:character_inactivate", "inactive", 403),  # Not in game
        ("gamer2", "games:character_reactivate", "pending", 403),  # Not in game
        (
            "gamer3",
            "games:character_inactivate",
            "inactive",
            403,
        ),  # In game but not owner
        (
            "gamer3",
            "games:character_reactivate",
            "pending",
            403,
        ),  # In game but not owner
        (
            "gamer1",
            "games:character_inactivate",
            "inactive",
            403,
        ),  # GM cannot manipulate
        (
            "gamer1",
            "games:character_reactivate",
            "pending",
            403,
        ),  # GM cannot manipulate
        ("gamer4", "games:character_inactivate", "inactive", 302),  # Character owner
        ("gamer4", "games:character_reactivate", "pending", 302),  # Character owner
    ],
)
def test_character_inactivate_reactivate_view(
    client,
    game_testdata,
    assert_login_redirect,
    gamer_to_use,
    view_name,
    status_to_send,
    expected_post_response,
):
    url = reverse(view_name, kwargs={"character": game_testdata.character1.slug})
    if status_to_send == "pending":
        game_testdata.character1.status = "inactive"
        game_testdata.character1.save()
        game_testdata.character1.refresh_from_db()
        assert game_testdata.character1.status == "inactive"
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    response = client.get(url)
    assert response.status_code == 405
    response = client.post(url, data={"status": status_to_send})
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_post_response
        updated_obj = models.Character.objects.get(id=game_testdata.character1.id)
        if expected_post_response == 302:
            assert updated_obj.status == status_to_send
        else:
            assert updated_obj.status != status_to_send


@pytest.mark.parametrize(
    "gamer_to_use, view_name, url_kwarg, url_item, expected_get_response, expected_items",
    [
        (None, "games:character_game_list", "gameid", "gp2", 302, None),
        (None, "games:character_player_list", "player", "player1", 302, None),
        (None, "games:character_gamer_list", None, None, 302, None),
        ("gamer2", "games:character_game_list", "gameid", "gp2", 403, None),
        ("gamer2", "games:character_player_list", "player", "player1", 403, None),
        ("gamer2", "games:character_gamer_list", None, None, 200, 0),
        ("gamer4", "games:character_game_list", "gameid", "gp2", 200, 2),
        ("gamer4", "games:character_player_list", "player", "player1", 200, 1),
        ("gamer4", "games:character_gamer_list", None, None, 200, 1),
        ("gamer3", "games:character_game_list", "gameid", "gp2", 200, 2),
        ("gamer3", "games:character_player_list", "player", "player1", 200, 1),
        ("gamer3", "games:character_gamer_list", None, None, 200, 1),
        ("gamer1", "games:character_game_list", "gameid", "gp2", 200, 2),
        ("gamer1", "games:character_player_list", "player", "player1", 200, 1),
        ("gamer1", "games:character_gamer_list", None, None, 200, 0),
    ],
)
def test_character_list_views(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    view_name,
    url_kwarg,
    url_item,
    expected_get_response,
    expected_items,
):
    models.Character.objects.create(
        player=game_testdata.player2,
        game=game_testdata.gp2,
        name="Taako",
        description="So magical.",
        status="approved",
    )
    game_testdata.character1.status = "approved"
    game_testdata.character1.save()
    url_kwargs = None
    if url_kwarg and url_item:
        url_kwargs = {url_kwarg: getattr(game_testdata, url_item).slug}
    url = reverse(view_name, kwargs=url_kwargs)
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(url)
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
        if expected_get_response == 200:
            assert len(response.context["object_list"]) == expected_items


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer2", 403), ("gamer4", 403), ("gamer1", 200)],
)
def test_game_invite_list_test(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    for x in range(3):
        Invite.objects.create(
            creator=game_testdata.gamer1.user,
            label="test {}".format(x),
            content_object=game_testdata.gp2,
        )
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse("games:game_invite_list", kwargs={"slug": game_testdata.gp2.slug})
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer2", 403), ("gamer4", 403), ("gamer1", 200)],
)
def test_game__export_view(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse("games:game_export", kwargs={"gameid": game_testdata.gp2.slug})
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response


@pytest.mark.parametrize(
    "gamer_to_use, expected_get_response",
    [(None, 302), ("gamer2", 403), ("gamer4", 403), ("gamer3", 403), ("gamer1", 200)],
)
def test_profile_export(
    client,
    game_testdata,
    django_assert_max_num_queries,
    assert_login_redirect,
    gamer_to_use,
    expected_get_response,
):
    if gamer_to_use:
        client.force_login(user=getattr(game_testdata, gamer_to_use).user)
    with django_assert_max_num_queries(50):
        response = client.get(
            reverse(
                "gamer_profiles:profile_export",
                kwargs={"gamer": game_testdata.gamer1.username},
            )
        )
    if not gamer_to_use:
        assert assert_login_redirect(response)
    else:
        assert response.status_code == expected_get_response
