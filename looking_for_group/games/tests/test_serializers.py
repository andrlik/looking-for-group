import pytest
from rest_framework.reverse import reverse

from ...game_catalog import models as catalog_models
from ...game_catalog import serializers as catalog_serializers
from .. import models, serializers

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "model, serializer_class",
    [
        (catalog_models.GamePublisher, catalog_serializers.GamerPublisherSerializer),
        (catalog_models.PublishedGame, catalog_serializers.PublishedGamerSerializer),
        (catalog_models.GameSystem, catalog_serializers.GameSystemSerializer),
        (catalog_models.GameEdition, catalog_serializers.GameEditionSerializer),
        (catalog_models.SourceBook, catalog_serializers.SourcebookSerializer),
        (catalog_models.PublishedModule, catalog_serializers.PublishedModuleSerializer),
    ],
)
def test_find_slug_in_url(catalog_testdata, model, serializer_class):
    """
    Test our ability to find the slugs in the testdata.
    """
    for item in model.objects.all():
        print(
            "Preparing test for item {}, with serializer class {}".format(
                item, serializer_class
            )
        )
        assert (
            serializers.find_slug_in_url(
                serializer_class(item, context={"request": None}).data["api_url"]
            )
            == item.slug
        )


@pytest.mark.parametrize(
    "gamertouse,edition,system,module,expected_valid",
    [
        ("gamer1", "numen", "cypher", "vv", True),
        (None, "numen", "cypher", "vv", True),
        ("gamer1", "numen", "ddfive", "vv", False),
        ("gamer1", "numen", "ddfive", None, False),
        ("gamer1", None, "cypher", None, True),
        ("gamer1", None, "cypher", "vv", True),
        ("gamer1", None, None, "vv", True),
        ("gamer1", "numen", None, None, True),
        ("gamer1", "numen", None, "cos", False),
        ("gamer1", None, None, None, True),
    ],
)
def test_game_serializer_validation(
    catalog_testdata,
    game_testdata,
    apiclient,
    gamertouse,
    edition,
    system,
    module,
    expected_valid,
):
    """
    Test the validation functions for a posted game.
    """
    request = None
    if gamertouse:
        apiclient.force_login(getattr(game_testdata, gamertouse).user)
        response = apiclient.get(
            reverse("api-game-detail", kwargs={"slug": game_testdata.gp1})
        )
        request = response.request
    existing_game = serializers.GameDataSerializer(
        game_testdata.gp1, context={"request": None}
    )
    new_game = {}
    for k, v in existing_game.data.items():
        if k not in [
            "api_url",
            "slug",
            "published_game",
            "game_system",
            "published_module",
        ]:
            new_game[k] = v
    if edition:
        new_game["published_game"] = reverse(
            "api-edition-detail",
            kwargs={
                "parent_lookup_game__slug": getattr(
                    catalog_testdata, edition
                ).game.slug,
                "slug": getattr(catalog_testdata, edition).slug,
            },
        )
    else:
        new_game["published_game"] = ""
    if system:
        new_game["game_system"] = reverse(
            "api-system-detail", kwargs={"slug": getattr(catalog_testdata, system).slug}
        )
    else:
        new_game["game_system"] = ""
    if module:
        new_game["published_module"] = reverse(
            "api-publishedmodule-detail",
            kwargs={
                "parent_lookup_parent_game_edition__game__slug": getattr(
                    catalog_testdata, module
                ).parent_game_edition.game.slug,
                "parent_lookup_parent_game_edition__slug": getattr(
                    catalog_testdata, module
                ).parent_game_edition.slug,
                "slug": getattr(catalog_testdata, module).slug,
            },
        )
    else:
        new_game["published_module"] = ""
    new_game["api_url"] = ""
    new_game["slug"] = ""
    print("Submitting data of value {} to serializer...".format(new_game))

    check_serializer = serializers.GameDataSerializer(
        data=new_game, context={"request": request}
    )
    validity_check = check_serializer.is_valid()
    print(check_serializer.errors)
    assert expected_valid == validity_check


@pytest.mark.parametrize(
    "privacy_level,communities_submitted,expected_result",
    [
        ("private", [], True),
        ("private", ["comm1"], False),
        ("community", ["comm1"], True),
        ("community", ["comm2"], False),
        ("community", ["comm1", "comm2"], False),
        ("public", [], True),
        ("public", ["comm1"], True),
        ("public", ["comm2"], False),
    ],
)
def test_game_serializer_community_logic(
    catalog_testdata,
    game_testdata,
    privacy_level,
    communities_submitted,
    expected_result,
):
    """
    Tests whether the community specific rules are being evaluated by the serializer validation for games correctly.
    """
    game_serialized = serializers.GameDataSerializer(
        game_testdata.gp2, context={"request": None}
    )
    game_update_data = game_serialized.data
    game_update_data["privacy_level"] = privacy_level
    game_update_data["communities"] = [
        getattr(game_testdata, c).slug for c in communities_submitted
    ]
    check_serial = serializers.GameDataSerializer(
        game_testdata.gp2, data=game_update_data, context={"request": None}
    )
    check_result = check_serial.is_valid()
    print(check_serial.errors)
    assert check_result == expected_result


@pytest.mark.parametrize(
    "players_expected,players_missing,expected_valid",
    [
        (["player1", "player2"], [], True),
        (["player1", "player2"], ["player1"], True),
        (["player1", "player2"], ["player1", "player2"], True),
        (["player1"], ["player2"], False),
        (["player1", "player2", "player3"], [], False),
    ],
)
def test_game_session_validation(
    game_testdata, players_expected, players_missing, expected_valid
):
    """
    Test the game session validator.
    """
    print("Starting to grab existing session data...")
    existing_session_data = serializers.GameSessionGMSerializer(
        game_testdata.session2, context={"request": None}
    ).data
    print("Got existing session data of {}".format(existing_session_data))
    print("Setting players_expected to {}".format(players_expected))
    existing_session_data["players_expected"] = [
        {"slug": p.slug, "gamer": p.gamer.username}
        for p in models.Player.objects.filter(
            pk__in=[getattr(game_testdata, g).pk for g in players_expected]
        )
    ]

    print("Setting players missing to {}".format(players_missing))
    existing_session_data["players_missing"] = [
        {"slug": p.slug, "gamer": p.gamer.username}
        for p in models.Player.objects.filter(
            pk__in=[getattr(game_testdata, g).pk for g in players_missing]
        )
    ]

    print(
        "Data to use to use in validation is now {}. Feeding to serializer...".format(
            existing_session_data
        )
    )
    check_serializer = serializers.GameSessionGMSerializer(
        instance=game_testdata.session2,
        data=existing_session_data,
        context={"request": None},
    )
    assert expected_valid == check_serializer.is_valid()
