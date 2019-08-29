import logging
from datetime import timedelta

from django.utils import timezone

from .models import Location

logger = logging.getLogger("locations")


def refresh_all_place_ids(age=30):
    """
    Refresh any location's place id where the modification timestamp is greater than age in days.
    """
    date_check = timezone.now() - timedelta(days=age)
    logger.debug("Checking for locations modified earlier than {}".format(date_check))
    locs = Location.objects.filter(
        modified__lte=date_check, google_place_id__isnull=False
    )
    logger.debug(
        "Retrieved {} locations needing to be refreshed...".format(locs.count())
    )
    if locs.count() > 0:
        for loc in locs:
            loc.refresh_place_id()
