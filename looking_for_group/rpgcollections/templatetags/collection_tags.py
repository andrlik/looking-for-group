from django import template
from django.contrib.contenttypes.models import ContentType

from ...game_catalog import models as catalog_models
from ..models import Book, GameLibrary
from ..utils import get_distinct_editions, get_distinct_games, get_distinct_publishers, get_distinct_systems

register = template.Library()


@register.simple_tag
def is_in_collection(obj, gamer):
    """
    For a given object and gamer, check to see if it exists in their game library.

    :retuns either the collected copy object or none
    """
    library, created = GameLibrary.objects.get_or_create(user=gamer.user)
    if not created:
        copy_count = obj.collected_copies.filter(library=library)
        if copy_count:
            return copy_count[0]
    return None


@register.simple_tag
def get_content_type(obj):
    ct = ContentType.objects.get_for_model(obj)
    return ct


@register.simple_tag
def get_collection_stats(gamer):
    """
    For a given gamer, return a dict of key stats about their rpg collection.
    """
    collection_data = {
        "total_books": 0,
        "total_print": 0,
        "total_pdf": 0,
        "sourcebooks": 0,
        "system_references": 0,
        "modules": 0,
        "num_games": 0,
        "num_editions": 0,
        "num_systems": 0,
        "num_publishers": 0,
        "source_library": None
    }
    sb_ct = ContentType.objects.get_for_model(catalog_models.SourceBook)
    sys_ct = ContentType.objects.get_for_model(catalog_models.GameSystem)
    md_ct = ContentType.objects.get_for_model(catalog_models.PublishedModule)
    library, created = GameLibrary.objects.get_or_create(user=gamer.user)
    collection_data["source_library"] = library
    if created:
        return collection_data
    whole_lib = Book.objects.filter(library=library)
    if whole_lib.count() == 0:
        return collection_data
    collection_data["total_books"] = whole_lib.count()
    collection_data["total_print"] = whole_lib.filter(in_print=True).count()
    collection_data["total_pdf"] = whole_lib.filter(in_pdf=True).count()
    collection_data["sourcebooks"] = whole_lib.filter(content_type=sb_ct).count()
    collection_data["system_references"] = whole_lib.filter(content_type=sys_ct).count()
    collection_data["modules"] = whole_lib.filter(content_type=md_ct).count()
    collection_data["num_games"] = get_distinct_games(library).count()
    collection_data["num_editions"] = get_distinct_editions(library).count()
    collection_data["num_systems"] = get_distinct_systems(library).count()
    collection_data["num_publishers"] = get_distinct_publishers(library).count()
    return collection_data
