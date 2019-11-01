import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete
from factory.django import mute_signals
from rest_framework.reverse import reverse

from .. import models, serializers

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "gamertouse,gametouse,viewname,httpmethod,post_data,expected_response,see_players",
    [
        (
            None,
            "gp1",
            "api-game-detail",
            "patch",
            {"title": "I am a brand new game"},
            403,
            False,
        ),
        (
            None,
            "gp1",
            "api-game-detail",
            "put",
            {"title": "I am a brand new game"},
            403,
            False,
        ),
        (None, "gp1", "api-game-detail", "delete", {}, 403, False),
        (
            "gamer1",
            "gp1",
            "api-game-detail",
            "patch",
            {"title": "I am a brand new game"},
            403,
            False,
        ),
        (
            "gamer1",
            "gp1",
            "api-game-detail",
            "put",
            {"title": "I am a brand new game"},
            403,
            False,
        ),
        ("gamer1", "gp1", "api-game-detail", "delete", {}, 403, False),
        (
            "gamer3",
            "gp1",
            "api-game-detail",
            "patch",
            {"title": "I am a brand new game"},
            403,
            False,
        ),
        (
            "gamer3",
            "gp1",
            "api-game-detail",
            "put",
            {"title": "I am a brand new game"},
            403,
            False,
        ),
        ("gamer3", "gp1", "api-game-detail", "delete", {}, 403, False),
        (
            "gamer4",
            "gp1",
            "api-game-detail",
            "patch",
            {"title": "I am a brand new game"},
            200,
            True,
        ),
        (
            "gamer4",
            "gp1",
            "api-game-detail",
            "put",
            {"title": "I am a brand new game"},
            200,
            True,
        ),
        ("gamer4", "gp1", "api-game-detail", "delete", {}, 204, False),
        (
            None,
            None,
            "api-game-list",
            "post",
            {
                "api_url": "",
                "slug": "",
                "title": "Dancing in the card",
                "gm": "testuser",
                "gm_stats": {
                    "games_created": 1,
                    "active_games": 1,
                    "games_finished": 0,
                },
                "game_description": "toga",
                "game_description_rendered": "<p>toga</p>",
                "game_type": "oneshot",
                "status": "open",
                "game_mode": "online",
                "privacy_level": "private",
                "adult_themes": False,
                "content_warning": None,
                "published_game": None,
                "published_game_title": None,
                "game_system": None,
                "game_system_name": None,
                "published_module": None,
                "published_module_title": None,
                "start_time": "2022-12-17T21:00:00-05:00",
                "session_length": "3.00",
                "end_date": None,
                "communities": [],
                "current_players": 0,
                "min_players": 1,
                "max_players": 3,
                "players": [],
                "sessions": 0,
                "player_stats": [],
                "created": "",
                "modified": "",
            },
            403,
            False,
        ),
        (
            "gamer1",
            None,
            "api-game-list",
            "post",
            {
                "api_url": "",
                "slug": "",
                "title": "Dancing in the card",
                "gm": "testuser",
                "gm_stats": {
                    "games_created": 1,
                    "active_games": 1,
                    "games_finished": 0,
                },
                "game_description": "toga",
                "game_description_rendered": "<p>toga</p>",
                "game_type": "oneshot",
                "status": "open",
                "game_mode": "online",
                "privacy_level": "private",
                "adult_themes": False,
                "content_warning": None,
                "published_game": None,
                "published_game_title": None,
                "game_system": None,
                "game_system_name": None,
                "published_module": None,
                "published_module_title": None,
                "start_time": "2022-12-17T21:00:00-05:00",
                "session_length": "3.00",
                "end_date": None,
                "communities": [],
                "current_players": 0,
                "min_players": 1,
                "max_players": 3,
                "players": [],
                "sessions": 0,
                "player_stats": [],
                "created": "",
                "modified": "",
            },
            201,
            True,
        ),
        (None, "gp1", "api-game-leave", "post", {}, 403, False),
        ("gamer4", "gp1", "api-game-leave", "post", {}, 400, False),
        ("gamer1", "gp1", "api-game-leave", "post", {}, 204, False),
        (
            None,
            "gp1",
            "api-game-apply",
            "post",
            {"api_url": "", "game": "", "gamer": "", "message": "Test"},
            403,
            False,
        ),
        (
            "gamer1",
            "gp1",
            "api-game-apply",
            "post",
            {"api_url": "", "game": "", "gamer": "", "message": "Test"},
            400,
            False,
        ),
        (
            "gamer3",
            "gp1",
            "api-game-apply",
            "post",
            {"api_url": "", "game": "", "gamer": "", "message": "Test"},
            201,
            False,
        ),
        (
            "gamer4",
            "gp1",
            "api-game-apply",
            "post",
            {"api_url": "", "game": "", "gamer": "", "message": "Test"},
            400,
            False,
        ),
    ],
)
def test_game_crud_views(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    gametouse,
    viewname,
    httpmethod,
    post_data,
    expected_response,
    see_players,
):
    gamer = None
    game = None
    current_players = None
    current_applications = None
    url_kwargs = {}
    current_games = models.GamePosting.objects.count()
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if gametouse:
        game = getattr(game_testdata, gametouse)
        current_players = game.players.count()
        current_applications = models.GamePostingApplication.objects.filter(
            game=game
        ).count()
        url_kwargs["slug"] = game.slug
    data_to_post = post_data.copy()
    if httpmethod == "put" and game:
        for k, v in serializers.GameDataSerializer(
            game, context={"request": None}
        ).data.items():
            if k not in data_to_post.keys() and k not in [
                "gm_stats",
                "player_stats",
                "players",
                "game_description_rendered",
                "published_module_title",
                "game_system_name",
                "published_game_title",
                "current_players",
            ]:
                data_to_post[k] = v
    url = reverse(viewname, kwargs=url_kwargs)
    print(url)
    with django_assert_max_num_queries(50):
        with mute_signals(post_delete, pre_delete, post_save):
            print("Submitting request with post data of {}".format(data_to_post))
            response = getattr(apiclient, httpmethod)(url, data=data_to_post)
    print(response.data)
    assert response.status_code == expected_response
    if "list" in viewname and expected_response == 201:
        assert models.GamePosting.objects.count() - current_games == 1
    elif httpmethod in ["put", "patch"] and game and expected_response == 200:
        game.refresh_from_db()
        for k, v in post_data.items():
            assert (v == "" and not getattr(game, k)) or v == getattr(game, k)
    elif game and httpmethod == "delete":
        if expected_response == 204:
            with pytest.raises(ObjectDoesNotExist):
                models.GamePosting.objects.get(pk=game.pk)
        else:
            assert models.GamePosting.objects.get(pk=game.pk)
    elif "leave" in viewname:
        if expected_response == 204:
            assert (
                current_players - models.Player.objects.filter(game=game).count() == 1
            )
        else:
            assert current_players == models.Player.objects.filter(game=game).count()
    elif "apply" in viewname:
        if expected_response == 201:
            assert (
                models.GamePostingApplication.objects.filter(game=game).count()
                - current_applications
                == 1
            )
        else:
            assert (
                models.GamePostingApplication.objects.filter(game=game).count()
                == current_applications
            )
    else:
        if game:
            assert game == models.GamePosting.objects.get(pk=game.pk)


@pytest.mark.parametrize(
    "gamertouse,gametouse,viewname,expected_response,see_players",
    [
        (None, None, "api-game-list", 403, False),
        (None, "gp1", "api-game-detail", 403, False),
        ("gamer1", None, "api-game-list", 200, True),
        ("gamer1", "gp1", "api-game-detail", 200, True),
        ("gamer3", None, "api-game-list", 200, False),
        ("gamer3", "gp1", "api-game-detail", 200, False),
        ("gamer4", None, "api-game-list", 200, False),
        ("gamer4", "gp1", "api-game-detail", 200, True),
    ],
)
def test_list_retrieve_games(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    gametouse,
    viewname,
    expected_response,
    see_players,
):
    gamer = None
    game = None
    url_kwargs = {}
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if gametouse:
        game = getattr(game_testdata, gametouse)
        url_kwargs["slug"] = game.slug
    url = reverse(viewname, kwargs=url_kwargs)
    print(url)
    with django_assert_max_num_queries(50):
        response = apiclient.get(url)
    print(response.data)
    assert response.status_code == expected_response
    if game:
        if see_players:
            assert "players" in response.data.keys()
        else:
            with pytest.raises(KeyError):
                response.data["players"]


@pytest.mark.parametrize(
    "gamertouse,gametouse,viewname, httpmethod, applicationtouse,expected_response",
    [
        (None, "gp5", "api-gameapplication-list", "get", None, 403),
        (None, "gp5", "api-gameapplication-detail", "get", "app1", 403),
        (None, "gp5", "api-gameapplication-approve", "post", "app1", 403),
        (None, "gp5", "api-gameapplication-reject", "post", "app1", 403),
        ("gamer3", "gp5", "api-gameapplication-list", "get", None, 403),
        ("gamer3", "gp5", "api-gameapplication-detail", "get", "app1", 403),
        ("gamer3", "gp5", "api-gameapplication-approve", "post", "app1", 403),
        ("gamer3", "gp5", "api-gameapplication-reject", "post", "app1", 403),
        ("gamer1", "gp5", "api-gameapplication-list", "get", None, 403),
        ("gamer1", "gp5", "api-gameapplication-detail", "get", "app1", 403),
        ("gamer1", "gp5", "api-gameapplication-approve", "post", "app1", 403),
        ("gamer1", "gp5", "api-gameapplication-reject", "post", "app1", 403),
        ("gamer4", "gp1", "api-gameapplication-detail", "get", "app1", 404),
        ("gamer4", "gp5", "api-gameapplication-list", "get", None, 200),
        ("gamer4", "gp5", "api-gameapplication-detail", "get", "app1", 200),
        ("gamer4", "gp5", "api-gameapplication-approve", "post", "app1", 201),
        ("gamer4", "gp5", "api-gameapplication-reject", "post", "app1", 200),
    ],
)
def test_gm_application_view_approve_reject(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    gametouse,
    viewname,
    httpmethod,
    applicationtouse,
    expected_response,
):
    """
    Test the GM view of game applications and ensure that permissions are applied correctly.
    """
    gamer = None
    game = getattr(game_testdata, gametouse)
    application = None
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if applicationtouse:
        application = getattr(game_testdata, applicationtouse)
    if not application:
        url = reverse(viewname, kwargs={"parent_lookup_game__slug": game.slug})
    else:
        url = reverse(
            viewname,
            kwargs={"parent_lookup_game__slug": game.slug, "slug": application.slug},
        )
    with django_assert_max_num_queries(50):
        with mute_signals(post_save):
            response = getattr(apiclient, httpmethod)(url, data={})
    print(response.data)
    assert response.status_code == expected_response
    if application:
        application.refresh_from_db()
        if "approve" in viewname and expected_response == 201:
            assert application.status == "approve"
        elif "reject" in viewname and expected_response == 200:
            assert application.status == "deny"
        else:
            assert application.status == "pending"
