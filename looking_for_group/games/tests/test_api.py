from datetime import datetime, timedelta

import pytest
import pytz
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete
from django.utils import timezone
from factory.django import mute_signals
from rest_framework.reverse import reverse

from .. import models, serializers

pytestmark = pytest.mark.django_db(transaction=True)

tz = pytz.timezone("US/Eastern")


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


@pytest.mark.parametrize(
    "gamertouse,viewname,httpmethod,applicationtouse,post_data,expected_response",
    [
        (None, "api-mygameapplication-list", "get", None, {}, 403),
        (None, "api-mygameapplication-detail", "get", "app1", {}, 403),
        (
            None,
            "api-mygameapplication-detail",
            "put",
            "app1",
            {"message": "I'm feeling strong today"},
            403,
        ),
        (
            None,
            "api-mygameapplication-detail",
            "patch",
            "app1",
            {"message": "I'm feeling strong today"},
            403,
        ),
        (None, "api-mygameapplication-detail", "delete", "app1", {}, 403),
        ("gamer4", "api-mygameapplication-list", "get", None, {}, 200),
        ("gamer4", "api-mygameapplication-detail", "get", "app1", {}, 404),
        (
            "gamer4",
            "api-mygameapplication-detail",
            "put",
            "app1",
            {"message": "I'm feeling strong today"},
            404,
        ),
        (
            "gamer4",
            "api-mygameapplication-detail",
            "patch",
            "app1",
            {"message": "I'm feeling strong today"},
            404,
        ),
        ("gamer4", "api-mygameapplication-detail", "delete", "app1", {}, 404),
        ("gamer1", "api-mygameapplication-list", "get", None, {}, 200),
        ("gamer1", "api-mygameapplication-detail", "get", "app1", {}, 200),
        (
            "gamer1",
            "api-mygameapplication-detail",
            "put",
            "app1",
            {"message": "I'm feeling strong today"},
            200,
        ),
        (
            "gamer1",
            "api-mygameapplication-detail",
            "patch",
            "app1",
            {"message": "I'm feeling strong today"},
            200,
        ),
        ("gamer1", "api-mygameapplication-detail", "delete", "app1", {}, 204),
    ],
)
def test_player_application_viewset(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    viewname,
    httpmethod,
    applicationtouse,
    post_data,
    expected_response,
):
    """
    Test the player views of their applications.
    """
    gamer = None
    application = None
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if applicationtouse:
        application = getattr(game_testdata, applicationtouse)
    data_to_post = post_data.copy()
    if httpmethod == "put":
        for k, v in serializers.GameApplicationSerializer(
            application, context={"request": None}
        ).data.items():
            if k not in post_data.keys() and k not in ["gamer_username"]:
                data_to_post[k] = v
    if application:
        url = reverse(viewname, kwargs={"slug": application.slug})
    else:
        url = reverse(viewname)
    print(url)
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, data=data_to_post)
    print(response.data)
    assert response.status_code == expected_response
    if expected_response == 204:
        with pytest.raises(ObjectDoesNotExist):
            models.GamePostingApplication.objects.get(pk=application.pk)
    elif httpmethod in ["put", "post"]:
        application.refresh_from_db()
        if expected_response == 200:
            for k, v in post_data.items():
                assert (v == "" and not getattr(application, k)) or v == getattr(
                    application, k
                )
        else:
            for k, v in post_data.items():
                assert v != getattr(application, k)
    else:
        if expected_response == 200:
            if not application:
                assert (
                    response.data["results"]
                    == serializers.GameApplicationSerializer(
                        models.GamePostingApplication.objects.filter(gamer=gamer),
                        many=True,
                        context={"request": response.wsgi_request},
                    ).data
                )
            else:
                application.refresh_from_db()
                assert (
                    response.data
                    == serializers.GameApplicationSerializer(
                        application, context={"request": response.wsgi_request}
                    ).data
                )


@pytest.mark.parametrize(
    "gamertouse,gametouse,viewname,httpmethod,chartouse,post_data,expected_response",
    [
        (None, "gp2", "api-character-list", "get", None, {}, 403),
        (
            None,
            "gp2",
            "api-character-list",
            "post",
            None,
            {
                "name": "Tommy",
                "description": "Just a jerk",
                "character_sheet": "",
                "status": "pending",
            },
            403,
        ),
        (None, "gp2", "api-character-detail", "get", "character1", {}, 403),
        (
            None,
            "gp2",
            "api-character-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            403,
        ),
        (
            None,
            "gp2",
            "api-character-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            403,
        ),
        (None, "gp2", "api-character-approve", "post", "character1", {}, 403),
        (None, "gp2", "api-character-reject", "post", "character1", {}, 403),
        (None, "gp2", "api-character-deactivate", "post", "character1", {}, 403),
        (None, "gp2", "api-character-reactivate", "post", "character1", {}, 403),
        (None, "gp2", "api-character-detail", "delete", "character1", {}, 403),
        ("gamer2", "gp2", "api-character-list", "get", None, {}, 403),
        (
            "gamer2",
            "gp2",
            "api-character-list",
            "post",
            None,
            {
                "name": "Tommy",
                "description": "Just a jerk",
                "character_sheet": "",
                "status": "pending",
            },
            403,
        ),
        ("gamer2", "gp2", "api-character-detail", "get", "character1", {}, 403),
        (
            "gamer2",
            "gp2",
            "api-character-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            403,
        ),
        (
            "gamer2",
            "gp2",
            "api-character-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            403,
        ),
        ("gamer2", "gp2", "api-character-approve", "post", "character1", {}, 403),
        ("gamer2", "gp2", "api-character-reject", "post", "character1", {}, 403),
        ("gamer2", "gp2", "api-character-deactivate", "post", "character1", {}, 403),
        ("gamer2", "gp2", "api-character-reactivate", "post", "character1", {}, 403),
        ("gamer2", "gp2", "api-character-detail", "delete", "character1", {}, 403),
        ("gamer3", "gp2", "api-character-list", "get", None, {}, 200),
        (
            "gamer3",
            "gp2",
            "api-character-list",
            "post",
            None,
            {
                "name": "Tommy",
                "description": "Just a jerk",
                "character_sheet": "",
                "status": "pending",
            },
            201,
        ),
        ("gamer3", "gp2", "api-character-detail", "get", "character1", {}, 200),
        (
            "gamer3",
            "gp2",
            "api-character-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            403,
        ),
        (
            "gamer3",
            "gp2",
            "api-character-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            403,
        ),
        ("gamer3", "gp2", "api-character-approve", "post", "character1", {}, 403),
        ("gamer3", "gp2", "api-character-reject", "post", "character1", {}, 403),
        ("gamer3", "gp2", "api-character-deactivate", "post", "character1", {}, 403),
        ("gamer3", "gp2", "api-character-reactivate", "post", "character1", {}, 403),
        ("gamer3", "gp2", "api-character-detail", "delete", "character1", {}, 403),
        ("gamer4", "gp2", "api-character-list", "get", None, {}, 200),
        (
            "gamer4",
            "gp2",
            "api-character-list",
            "post",
            None,
            {
                "name": "Tommy",
                "description": "Just a jerk",
                "character_sheet": "",
                "status": "pending",
            },
            201,
        ),
        ("gamer4", "gp2", "api-character-detail", "get", "character1", {}, 200),
        (
            "gamer4",
            "gp2",
            "api-character-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            200,
        ),
        (
            "gamer4",
            "gp2",
            "api-character-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            200,
        ),
        ("gamer4", "gp2", "api-character-approve", "post", "character1", {}, 403),
        ("gamer4", "gp2", "api-character-reject", "post", "character1", {}, 403),
        ("gamer4", "gp2", "api-character-deactivate", "post", "character1", {}, 200),
        ("gamer4", "gp2", "api-character-reactivate", "post", "character1", {}, 200),
        ("gamer4", "gp2", "api-character-detail", "delete", "character1", {}, 204),
        ("gamer1", "gp2", "api-character-list", "get", None, {}, 200),
        (
            "gamer1",
            "gp2",
            "api-character-list",
            "post",
            None,
            {
                "name": "Tommy",
                "description": "Just a jerk",
                "character_sheet": "",
                "status": "pending",
            },
            403,
        ),
        ("gamer1", "gp2", "api-character-detail", "get", "character1", {}, 200),
        (
            "gamer1",
            "gp2",
            "api-character-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            200,
        ),
        (
            "gamer1",
            "gp2",
            "api-character-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot"},
            200,
        ),
        ("gamer1", "gp2", "api-character-approve", "post", "character1", {}, 200),
        ("gamer1", "gp2", "api-character-reject", "post", "character1", {}, 200),
        ("gamer1", "gp2", "api-character-deactivate", "post", "character1", {}, 403),
        ("gamer1", "gp2", "api-character-reactivate", "post", "character1", {}, 403),
        ("gamer1", "gp2", "api-character-detail", "delete", "character1", {}, 403),
    ],
)
def test_character_game_viewset(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    gametouse,
    viewname,
    httpmethod,
    chartouse,
    post_data,
    expected_response,
):
    """
    Tests for the game-centric character viewset.
    """
    gamer = None
    game = getattr(game_testdata, gametouse)
    character = None
    character_count = models.Character.objects.count()
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if chartouse:
        character = getattr(game_testdata, chartouse)
    data_to_post = post_data.copy()
    if httpmethod == "put":
        for k, v in serializers.CharacterSerializer(
            character, context={"request": None}
        ).data.items():
            if k not in post_data.keys() and k not in ["created", "modified", "player"]:
                data_to_post[k] = v
    if character:
        url = reverse(
            viewname,
            kwargs={"parent_lookup_game__slug": game.slug, "slug": character.slug},
        )
    else:
        url = reverse(viewname, kwargs={"parent_lookup_game__slug": game.slug})
    print(url)
    print(
        "Preparing to submit request to {} with {} for {} ({})".format(
            url, data_to_post, gamer, gamertouse
        )
    )
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, data=data_to_post)
    print(response.data)
    assert response.status_code == expected_response
    if character:
        if expected_response == 204:
            with pytest.raises(ObjectDoesNotExist):
                models.Character.objects.get(pk=character.pk)
        elif expected_response == 200:
            character.refresh_from_db()
            if httpmethod in ["put", "patch"]:
                for k, v in post_data.items():
                    assert (v == "" and not getattr(character, k)) or v == getattr(
                        character, k
                    )
            else:
                for k, v in post_data.items():
                    assert v != getattr(character, k)
        else:
            assert models.Character.objects.get(pk=character.pk)
    else:
        if expected_response == 201:
            assert models.Character.objects.count() - character_count == 1
        else:
            assert models.Character.objects.count() == character_count


@pytest.mark.parametrize(
    "gamertouse,viewname,httpmethod,chartouse,post_data,expected_response",
    [
        (None, "api-mycharacter-list", "get", None, {}, 403),
        (None, "api-mycharacter-detail", "get", "character1", {}, 403),
        (
            None,
            "api-mycharacter-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            403,
        ),
        (
            None,
            "api-mycharacter-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            403,
        ),
        (None, "api-mycharacter-detail", "delete", "character1", {}, 403),
        (None, "api-mycharacter-deactivate", "post", "character1", {}, 403),
        (None, "api-mycharacter-reactivate", "post", "character1", {}, 403),
        ("gamer2", "api-mycharacter-list", "get", None, {}, 200),
        ("gamer2", "api-mycharacter-detail", "get", "character1", {}, 404),
        (
            "gamer2",
            "api-mycharacter-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            404,
        ),
        (
            "gamer2",
            "api-mycharacter-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            404,
        ),
        ("gamer2", "api-mycharacter-detail", "delete", "character1", {}, 404),
        ("gamer2", "api-mycharacter-deactivate", "post", "character1", {}, 404),
        ("gamer2", "api-mycharacter-reactivate", "post", "character1", {}, 404),
        ("gamer1", "api-mycharacter-list", "get", None, {}, 200),
        ("gamer1", "api-mycharacter-detail", "get", "character1", {}, 404),
        (
            "gamer1",
            "api-mycharacter-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            404,
        ),
        (
            "gamer1",
            "api-mycharacter-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            404,
        ),
        ("gamer1", "api-mycharacter-detail", "delete", "character1", {}, 404),
        ("gamer1", "api-mycharacter-deactivate", "post", "character1", {}, 404),
        ("gamer1", "api-mycharacter-reactivate", "post", "character1", {}, 404),
        ("gamer4", "api-mycharacter-list", "get", None, {}, 200),
        ("gamer4", "api-mycharacter-detail", "get", "character1", {}, 200),
        (
            "gamer4",
            "api-mycharacter-detail",
            "patch",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            200,
        ),
        (
            "gamer4",
            "api-mycharacter-detail",
            "put",
            "character1",
            {"description": "Barry bluejeans is my co-pilot."},
            200,
        ),
        ("gamer4", "api-mycharacter-detail", "delete", "character1", {}, 204),
        ("gamer4", "api-mycharacter-deactivate", "post", "character1", {}, 200),
        ("gamer4", "api-mycharacter-reactivate", "post", "character1", {}, 200),
    ],
)
def test_my_character_viewset(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    viewname,
    httpmethod,
    chartouse,
    post_data,
    expected_response,
):
    """
    Tests the viewset for a given game to see all of their characters.
    """
    gamer = None
    character = None
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if chartouse:
        character = getattr(game_testdata, chartouse)
    data_to_post = post_data.copy()
    if httpmethod == "put":
        for k, v in serializers.CharacterSerializer(
            character, context={"request": None}
        ).data.items():
            if k not in post_data.keys() and k not in [
                "player",
                "player_username",
                "game",
            ]:
                data_to_post[k] = v
    if character:
        url = reverse(viewname, kwargs={"slug": character.slug})
    else:
        url = reverse(viewname)
    print(url)
    print(
        "Preparing to submit {} to url {} for {}".format(data_to_post, url, gamertouse)
    )
    with django_assert_max_num_queries(50):
        response = getattr(apiclient, httpmethod)(url, data=data_to_post)
    print(response.data)
    assert response.status_code == expected_response
    if expected_response == 204:
        with pytest.raises(ObjectDoesNotExist):
            models.Character.objects.get(pk=character.pk)
    elif httpmethod in ["put", "patch"]:
        character.refresh_from_db()
        if expected_response == 200:
            for k, v in post_data.items():
                assert (v == "" and not getattr(character, k)) or getattr(
                    character, k
                ) == v
        else:
            for k, v in post_data.items():
                assert getattr(character, k) != v
    else:
        if character and httpmethod == "delete":
            assert models.Character.objects.get(pk=character.pk)


@pytest.mark.parametrize(
    "gamertouse,gametouse,viewname,httpmethod,sessiontouse,post_data,expected_response",
    [
        (None, "gp2", "api-session-list", "get", None, {}, 403),
        (None, "gp2", "api-session-detail", "get", "session2", {}, 403),
        (
            None,
            "gp2",
            "api-session-detail",
            "put",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            403,
        ),
        (
            None,
            "gp2",
            "api-session-detail",
            "patch",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            403,
        ),
        (None, "gp2", "api-session-detail", "delete", "session2", {}, 403),
        (
            None,
            "gp2",
            "api-session-reschedule",
            "post",
            "session2",
            {
                "new_scheduled_time": (timezone.now() + timedelta(days=30))
                .astimezone(tz)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            403,
        ),
        (None, "gp2", "api-session-cancel", "post", "session2", {}, 403),
        (None, "gp2", "api-session-uncancel", "post", "session2", {}, 403),
        (None, "gp2", "api-session-complete", "post", "session2", {}, 403),
        (None, "gp2", "api-session-uncomplete", "post", "session2", {}, 403),
        (
            None,
            "gp2",
            "api-session-addlog",
            "post",
            "session2",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            403,
        ),
        (
            None,
            "gp2",
            "api-session-addlog",
            "post",
            "session1",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            403,
        ),
        ("gamer2", "gp2", "api-session-list", "get", None, {}, 403),
        ("gamer2", "gp2", "api-session-detail", "get", "session2", {}, 403),
        (
            "gamer2",
            "gp2",
            "api-session-detail",
            "put",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            403,
        ),
        (
            "gamer2",
            "gp2",
            "api-session-detail",
            "patch",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            403,
        ),
        ("gamer2", "gp2", "api-session-detail", "delete", "session2", {}, 403),
        (
            "gamer2",
            "gp2",
            "api-session-reschedule",
            "post",
            "session2",
            {
                "new_scheduled_time": (timezone.now() + timedelta(days=30))
                .astimezone(tz)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            403,
        ),
        ("gamer2", "gp2", "api-session-cancel", "post", "session2", {}, 403),
        ("gamer2", "gp2", "api-session-uncancel", "post", "session2", {}, 403),
        ("gamer2", "gp2", "api-session-complete", "post", "session2", {}, 403),
        ("gamer2", "gp2", "api-session-uncomplete", "post", "session2", {}, 403),
        (
            "gamer2",
            "gp2",
            "api-session-addlog",
            "post",
            "session1",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            403,
        ),
        (
            "gamer2",
            "gp2",
            "api-session-addlog",
            "post",
            "session2",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            403,
        ),
        ("gamer4", "gp2", "api-session-list", "get", None, {}, 200),
        ("gamer4", "gp2", "api-session-detail", "get", "session2", {}, 200),
        (
            "gamer4",
            "gp2",
            "api-session-detail",
            "put",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            403,
        ),
        (
            "gamer4",
            "gp2",
            "api-session-detail",
            "patch",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            403,
        ),
        ("gamer4", "gp2", "api-session-detail", "delete", "session2", {}, 403),
        (
            "gamer4",
            "gp2",
            "api-session-reschedule",
            "post",
            "session2",
            {
                "new_scheduled_time": (timezone.now() + timedelta(days=30))
                .astimezone(tz)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            403,
        ),
        ("gamer4", "gp2", "api-session-cancel", "post", "session2", {}, 403),
        ("gamer4", "gp2", "api-session-uncancel", "post", "session2", {}, 403),
        ("gamer4", "gp2", "api-session-complete", "post", "session2", {}, 403),
        ("gamer4", "gp2", "api-session-uncomplete", "post", "session2", {}, 403),
        (
            "gamer4",
            "gp2",
            "api-session-addlog",
            "post",
            "session2",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            400,
        ),
        (
            "gamer4",
            "gp2",
            "api-session-addlog",
            "post",
            "session1",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            201,
        ),
        ("gamer1", "gp2", "api-session-list", "get", None, {}, 200),
        ("gamer1", "gp2", "api-session-detail", "get", "session2", {}, 200),
        (
            "gamer1",
            "gp2",
            "api-session-detail",
            "put",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            200,
        ),
        (
            "gamer1",
            "gp2",
            "api-session-detail",
            "patch",
            "session2",
            {
                "gm_notes": "A whole lot of madness going on.",
                "players_expected": ["player1", "player2"],
                "players_missing": ["player2"],
            },
            200,
        ),
        ("gamer1", "gp2", "api-session-detail", "delete", "session2", {}, 204),
        (
            "gamer1",
            "gp2",
            "api-session-reschedule",
            "post",
            "session2",
            {
                "new_scheduled_time": (timezone.now() + timedelta(days=30))
                .astimezone(tz)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            200,
        ),
        (
            "gamer1",
            "gp2",
            "api-session-reschedule",
            "post",
            "session1",
            {
                "new_scheduled_time": (timezone.now() + timedelta(days=30))
                .astimezone(tz)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            400,
        ),
        ("gamer1", "gp2", "api-session-cancel", "post", "session2", {}, 200),
        ("gamer1", "gp2", "api-session-uncancel", "post", "session2", {}, 400),
        ("gamer1", "gp2", "api-session-complete", "post", "session2", {}, 200),
        ("gamer1", "gp2", "api-session-complete", "post", "session1", {}, 400),
        ("gamer1", "gp2", "api-session-uncomplete", "post", "session2", {}, 400),
        ("gamer1", "gp2", "api-session-uncomplete", "post", "session1", {}, 200),
        (
            "gamer1",
            "gp2",
            "api-session-addlog",
            "post",
            "session2",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            400,
        ),
        (
            "gamer1",
            "gp2",
            "api-session-addlog",
            "post",
            "session1",
            {"title": "We had some fun", "body": "Didn't we, boys?"},
            201,
        ),
    ],
)
def test_game_session_viewset(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    gametouse,
    viewname,
    httpmethod,
    sessiontouse,
    post_data,
    expected_response,
):
    """
    Test game session actions.
    """
    gamer = None
    game = getattr(game_testdata, gametouse)
    session = None
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    if sessiontouse:
        session = getattr(game_testdata, sessiontouse)
    data_to_post = post_data.copy()
    if "players_expected" in post_data.keys():
        data_to_post["players_expected"] = [
            {"game": p.game.slug, "gamer": p.gamer.username}
            for p in [
                getattr(game_testdata, player)
                for player in post_data["players_expected"]
            ]
        ]
    if "players_missing" in post_data.keys():
        data_to_post["players_missing"] = [
            {"game": p.game.slug, "gamer": p.gamer.username}
            for p in [
                getattr(game_testdata, player)
                for player in post_data["players_missing"]
            ]
        ]
    if httpmethod == "put":
        for k, v in serializers.GameSessionGMSerializer(
            session, context={"request": None}
        ).data.items():
            if k not in post_data.keys() and k not in [
                "created",
                "modified",
                "api_url",
                "game",
                "gm_notes_rendered",
            ]:
                data_to_post[k] = v
    if session:
        url = reverse(
            viewname,
            kwargs={"parent_lookup_game__slug": game.slug, "slug": session.slug},
        )
    else:
        url = reverse(viewname, kwargs={"parent_lookup_game__slug": game.slug})
    print(url)
    print(
        "Preparing to send {} to url {} for user {}...".format(
            data_to_post, url, gamertouse
        )
    )
    with django_assert_max_num_queries(50):
        with mute_signals(post_save):
            response = getattr(apiclient, httpmethod)(url, data=data_to_post)
    print(
        "Expected {}. Got {}: {}".format(
            expected_response, response.status_code, response.data
        )
    )
    assert response.status_code == expected_response
    if session:
        if expected_response == 204:
            with pytest.raises(ObjectDoesNotExist):
                models.GameSession.objects.get(pk=session.pk)
        else:
            session.refresh_from_db()
            session_serialized = serializers.GameSessionGMSerializer(
                session, context={"request": None}
            )
            if httpmethod in ["put", "patch"]:
                if expected_response == 200:
                    for k, v in post_data.items():
                        if "players" in k:
                            assert session.players_expected.count() == 2
                            assert session.players_missing.count() == 1
                        else:
                            assert v == session_serialized.data[k]
                else:
                    for k, v in post_data.items():
                        assert v != session_serialized.data[k]
            elif "reschedule" in viewname:
                if expected_response == 200:
                    assert (
                        datetime.strptime(
                            post_data["new_scheduled_time"], "%Y-%m-%dT%H:%M:%S%z"
                        )
                        == session.scheduled_time
                    )
                else:
                    assert (
                        datetime.strptime(
                            post_data["new_scheduled_time"], "%Y-%m-%dT%H:%M:%S%z"
                        )
                        != session.scheduled_time
                    )
            elif "-cancel" in viewname:
                if expected_response == 200:
                    assert session.status == "cancel"
                elif expected_response != 400:
                    assert session.status != "cancel"
            elif "-complete" in viewname:
                if expected_response == 200:
                    assert session.status == "complete"
                elif expected_response != 400:
                    assert session.status != "complete"
            elif "add_log" in viewname:
                if expected_response == 201:
                    assert session.log
            else:
                assert models.GameSession.objects.get(pk=session.pk)


@pytest.mark.parametrize(
    "gamertouse,gametouse,sessiontouse,logtouse,viewname,httpmethod,post_data,expected_response",
    [
        (None, "gp2", "session2", "log1", "api-adventurelog-detail", "get", {}, 403),
        (
            None,
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "patch",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            403,
        ),
        (
            None,
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "put",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            403,
        ),
        (None, "gp2", "session2", "log1", "api-adventurelog-detail", "delete", {}, 403),
        (
            "gamer2",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "get",
            {},
            403,
        ),
        (
            "gamer2",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "patch",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            403,
        ),
        (
            "gamer2",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "put",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            403,
        ),
        (
            "gamer2",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "delete",
            {},
            403,
        ),
        (
            "gamer4",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "get",
            {},
            200,
        ),
        (
            "gamer4",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "patch",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            200,
        ),
        (
            "gamer4",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "put",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            200,
        ),
        (
            "gamer4",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "delete",
            {},
            403,
        ),
        (
            "gamer1",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "get",
            {},
            200,
        ),
        (
            "gamer1",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "patch",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            200,
        ),
        (
            "gamer1",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "put",
            {
                "body": "We got to all the secret rooms and stole mad loot. Murderhobos for life!"
            },
            200,
        ),
        (
            "gamer1",
            "gp2",
            "session2",
            "log1",
            "api-adventurelog-detail",
            "delete",
            {},
            204,
        ),
    ],
)
def test_adventure_log_viewset(
    apiclient,
    game_testdata,
    django_assert_max_num_queries,
    gamertouse,
    gametouse,
    sessiontouse,
    logtouse,
    viewname,
    httpmethod,
    post_data,
    expected_response,
):
    """
    Tests for the adventure log view set.
    """
    gamer = None
    game = getattr(game_testdata, gametouse)
    session = getattr(game_testdata, sessiontouse)
    log = getattr(game_testdata, logtouse)
    if gamertouse:
        gamer = getattr(game_testdata, gamertouse)
        apiclient.force_login(gamer.user)
    data_to_post = post_data.copy()
    if httpmethod == "put":
        for k, v in serializers.AdventureLogSerializer(
            log, context={"request": None}
        ).data.items():
            if k not in post_data.keys() and k not in [
                "created",
                "modified",
                "session",
                "api_url",
                "body_rendered",
            ]:
                data_to_post[k] = v
    url = reverse(
        viewname,
        kwargs={
            "parent_lookup_session__game__slug": game.slug,
            "parent_lookup_session__slug": session.slug,
            "slug": log.slug,
        },
    )
    print(url)
    print(
        "Preparing to submit {} to {} for user {}...".format(
            data_to_post, url, gamertouse
        )
    )
    with django_assert_max_num_queries(50):
        with mute_signals(post_save):
            response = getattr(apiclient, httpmethod)(url, data=data_to_post)
    print(
        "Expected {}. Got {}: {}".format(
            expected_response, response.status_code, response.data
        )
    )
    assert response.status_code == expected_response
    if expected_response == 204:
        with pytest.raises(ObjectDoesNotExist):
            models.AdventureLog.objects.get(pk=log.pk)
    else:
        log.refresh_from_db()
        log_serial = serializers.AdventureLogSerializer(log, context={"request": None})
        if httpmethod in ["put", "patch"]:
            if expected_response == 200:
                for k, v in post_data.items():
                    assert log_serial.data[k] == v
            else:
                for k, v in post_data.items():
                    assert log_serial.data[k] != v
        assert models.AdventureLog.objects.get(pk=log.pk)
