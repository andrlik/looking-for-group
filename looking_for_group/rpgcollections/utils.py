from django.contrib.contenttypes.models import ContentType

from ..game_catalog import models as catalog_models
from . import models


def get_distinct_games(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sourcebook_games = catalog_models.PublishedGame.objects.filter(
        id__in=[
            sb.edition.game.pk
            for sb in catalog_models.SourceBook.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sb_ct
                    )
                ]
            ).select_related("edition", "edition__game")
        ]
    ).order_by("title")
    module_games = catalog_models.PublishedGame.objects.filter(
        id__in=[
            md.parent_game_edition.game.pk
            for md in catalog_models.PublishedModule.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=md_ct
                    )
                ]
            ).select_related("parent_game_edition", "parent_game_edition__game")
        ]
    ).order_by("title")
    games = sourcebook_games.union(module_games).order_by("title")
    return games


def get_distinct_editions(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sourcebook_editions = (
        catalog_models.GameEdition.objects.filter(
            id__in=[
                sb.edition.pk
                for sb in catalog_models.SourceBook.objects.filter(
                    id__in=[
                        b.content_object.pk
                        for b in models.Book.objects.filter(
                            library=library, content_type=sb_ct
                        )
                    ]
                ).select_related("edition")
            ]
        )
        .select_related("game")
        .order_by("game__title", "release_date")
    )
    module_editions = (
        catalog_models.GameEdition.objects.filter(
            id__in=[
                md.parent_game_edition.pk
                for md in catalog_models.PublishedModule.objects.filter(
                    id__in=[
                        b.content_object.pk
                        for b in models.Book.objects.filter(
                            library=library, content_type=md_ct
                        )
                    ]
                ).select_related("parent_game_edition")
            ]
        )
        .select_related("game")
        .order_by("game__title", "release_date")
    )
    editions = sourcebook_editions.union(module_editions).order_by(
        "game__title", "release_date"
    )
    return editions


def get_distinct_systems(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sys_ct = ContentType.objects.get_for_model(catalog_models.GameSystem)
    sourcebook_systems = catalog_models.GameSystem.objects.filter(
        id__in=[
            sb.edition.game_system.pk
            for sb in catalog_models.SourceBook.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sb_ct
                    )
                ],
                edition__game_system__isnull=False,
            ).select_related("edition", "edition__game_system")
        ]
    ).order_by("name", "publication_date")
    module_systems = catalog_models.GameSystem.objects.filter(
        id__in=[
            md.parent_game_edition.game_system.pk
            for md in catalog_models.PublishedModule.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=md_ct
                    )
                ],
                parent_game_edition__game_system__isnull=False,
            ).select_related("parent_game_edition", "parent_game_edition__game_system")
        ]
    ).order_by("name", "publication_date")
    system_systems = catalog_models.GameSystem.objects.filter(
        id__in=[
            b.content_object.pk
            for b in models.Book.objects.filter(library=library, content_type=sys_ct)
        ]
    ).order_by("name", "publication_date")
    sb_and_md = sourcebook_systems.union(module_systems)
    systems = sb_and_md.union(system_systems).order_by("name", "publication_date")
    return systems


def get_distinct_publishers(library):
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    sys_ct = ContentType.objects.get_for_model(catalog_models.GameSystem)
    sourcebook_publishers = catalog_models.GamePublisher.objects.filter(
        id__in=[
            sb.publisher.pk
            for sb in catalog_models.SourceBook.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sb_ct
                    )
                ]
            )
        ]
    ).order_by("name")
    module_publishers = catalog_models.GamePublisher.objects.filter(
        id__in=[
            md.publisher.pk
            for md in catalog_models.PublishedModule.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=md_ct
                    )
                ]
            ).select_related("publisher")
        ]
    ).order_by("name")
    system_publishers = catalog_models.GamePublisher.objects.filter(
        id__in=[
            sys.original_publisher.pk
            for sys in catalog_models.GameSystem.objects.filter(
                id__in=[
                    b.content_object.pk
                    for b in models.Book.objects.filter(
                        library=library, content_type=sys_ct
                    )
                ]
            ).select_related("original_publisher")
        ]
    ).order_by("name")
    sb_and_md = sourcebook_publishers.union(module_publishers)
    publishers = sb_and_md.union(system_publishers).order_by("name")
    return publishers
