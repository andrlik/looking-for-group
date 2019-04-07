from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from ..game_catalog.models import SourceBook, PublishedModule, GameSystem
from . import models


def recalc_library_content(library):
    """
    For given library recalc all the denormalized stats.
    """
    sb_ct = ContentType.objects.get_for_model(SourceBook)
    pm_ct = ContentType.objects.get_for_model(PublishedModule)
    gs_ct = ContentType.objects.get_for_model(GameSystem)
    num_titles = models.Book.objects.filter(library=library).count()
    num_print = models.Book.objects.filter(library=library, in_print=True).count()
    num_pdf = models.Book.objects.filter(library=library, in_pdf=True).count()
    Q_sb = Q(content_type=sb_ct)
    Q_system = Q(content_type=gs_ct)
    distinct_sourcebooks = models.Book.objects.filter(library=library).filter(Q_sb | Q_system)
    distinct_modules = models.Book.objects.filter(library=library, content_type=pm_ct)
    library.num_titles = num_titles
    library.num_pdf = num_pdf
    library.num_print = num_print
    library.distinct_sourcebooks = distinct_sourcebooks.count()
    library.distinct_modules = distinct_modules.count()
    library.save()
