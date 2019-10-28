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
        assert (
            serializers.find_slug_in_url(
                serializer_class(item, context={"request": None}).data["api_url"]
            )
            == item.slug
        )


@pytest.mark.parametrize(
    "edition,system,module,expected_valid",
    [
        ("numen", "cypher", "vv", True),
        ("numen", "ddfive", "vv", False),
        ("numen", "ddfive", None, False),
        (None, "cypher", None, True),
        (None, "cypher", "vv", True),
        (None, None, "vv", True),
        ("numen", None, None, True),
        ("numen", None, "cos", False),
        (None, None, None, True),
    ],
)
def test_game_serializer_validation(
    catalog_testdata, game_testdata, edition, system, module, expected_valid
):
    """
    Test the validation functions for a posted game.
    """
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
                "slug": getattr(catalog_testdata, edition),
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
            "api-module_detail",
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
        new_game["published_module"] == ""
    new_game["api_url"] = ""
    new_game["slug"] = ""
    check_serializer = serializers.GameDataSerializer(data=new_game)
    assert expected_valid == check_serializer.is_valid()


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
    existing_session_data = serializers.GameSessionSerializer(
        game_testdata.session2, context={"request": None}
    ).data
    existing_session_data["players_expected"] = serializers.PlayerSerializer(
        [
            p
            for p in models.Player.objects.filter(
                gamer__username__in=[
                    getattr(p, "gamer").username for p in players_expected
                ]
            )
        ],
        many=True,
    )
    existing_session_data["players_missing"] = serializers.PlayerSerializer(
        [
            p
            for p in models.Player.objects.filter(
                gamer__username__in=[
                    getattr(p, "gamer").username for p in players_missing
                ]
            )
        ],
        many=True,
    )
    check_serializer = serializers.GameSessionSerializer(
        data=existing_session_data, context={"request": None}
    )
    assert expected_valid == check_serializer.is_valid()
