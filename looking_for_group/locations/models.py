from uuid import uuid4

from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

# Create your models here.


class AbstractUUIDGISModel(TimeStampedModel):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)

    class Meta:
        abstract = True


class Address(AbstractUUIDGISModel, models.Model):
    """
    Represents an address or named location (if provided by Google) to assosciate with a record.
    """

    google_place_name = models.CharField(
        _("Place Name"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Place name as retrieved from Google."),
    )
    google_place_id = models.CharField(
        _("Place ID"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Google place id"),
        db_index=True,
    )
    formatted_address = models.CharField(
        _("Formatted Address"),
        max_length=255,
        help_text=_("The address as one text string."),
    )
    location = models.PointField(
        _("Geolocation"),
        null=True,
        blank=True,
        help_text=_("A point representing the lat and long of the location."),
    )
    viewport_nw = models.PointField(
        _("NW corner of recommended viewport"),
        null=True,
        blank=True,
        help_text=_("Recommended NW of viewport for map display"),
    )
    viewport_se = models.PointField(
        _("SE corner of recommended viewport"),
        null=True,
        blank=True,
        help_text=_("Recommended SE of viewport for map display"),
    )
    city = models.CharField(
        _("City"),
        null=True,
        blank=True,
        max_length=255,
        help_text=_("City as returned by geocoder."),
    )
    state = models.CharField(
        _("State"),
        null=True,
        blank=True,
        max_length=255,
        help_text=_("State as returned by geocoder."),
    )
    country = models.CharField(
        _("Country"),
        null=True,
        blank=True,
        max_length=90,
        help_text=_("Country as returned by geocoder."),
    )
    location_accuracy = models.CharField(
        max_lenth=50,
        null=True,
        blank=True,
        help_text=_("Google's location type, e.g. ROOFTOP"),
        db_index=True,
    )

    def __str__(self):
        return self.formatted_address
