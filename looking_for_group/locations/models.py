import logging
from uuid import uuid4

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from geopy.geocoders import GoogleV3
from geopy.point import Point as GPyPoint
from model_utils.models import TimeStampedModel

# Create your models here.

logger = logging.getLogger("locations")


class AbstractUUIDGISModel(TimeStampedModel):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)

    class Meta:
        abstract = True


GEOCODE_TYPE_CHOICES = (("forward", _("Forward")), ("reverse", _("Reverse")))


class Location(AbstractUUIDGISModel, models.Model):
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
        _("Address"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Only accepted players can see this."),
    )
    latlong = models.PointField(
        _("Geolocation"),
        null=True,
        blank=True,
        help_text=_("A point representing the lat and long of the location."),
    )
    viewport_ne = models.PointField(
        _("NE corner of recommended viewport"),
        null=True,
        blank=True,
        help_text=_("Recommended NE of viewport for map display"),
    )
    viewport_sw = models.PointField(
        _("SW corner of recommended viewport"),
        null=True,
        blank=True,
        help_text=_("Recommended SW of viewport for map display"),
    )
    city = models.CharField(
        _("City"),
        null=True,
        blank=True,
        max_length=255,
        help_text=_("City as returned by geocoder."),
    )
    postal_code = models.CharField(
        _("Postal code"),
        null=True,
        blank=True,
        max_length=15,
        help_text=_("Postal code"),
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
        max_length=50,
        null=True,
        blank=True,
        help_text=_("Google's location type, e.g. ROOFTOP"),
        db_index=True,
    )
    geocode_method = models.CharField(
        max_length=15,
        choices=GEOCODE_TYPE_CHOICES,
        default="forward",
        help_text=_("What process was used for geocoding?"),
    )
    geocode_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_("How many times have we attempted to send this to the geocoder?"),
    )

    def __str__(self):
        return self.formatted_address

    @property
    def is_geocoded(self):
        """
        Has this record already been geocoded?

        :returns: True or False
        """
        if self.geocode_method == "reverse" and self.formatted_address:
            return True
        if self.geocode_method == "forward" and self.latlong:
            return True
        return False

    @property
    def google_map_url(self):
        if not self.is_geocoded:
            return None
        url = "https://www.google.com/maps/search/?api=1&query={},{}".format(
            self.latlong.y, self.latlong.x
        )
        if self.google_place_id:
            url = url + "&query_place_id={}".format(self.google_place_id)
        return url

    @property
    def google_map_embed_url(self):
        if not self.is_geocoded:
            return None
        url = "https://www.google.com/maps/embed/v1/search?q={},{}".format(
            self.latlong.y, self.latlong.x
        )
        # if self.google_place_id:
        #    url = url + "&query_place_id={}".format(self.google_place_id)
        return url + "&key={}".format(settings.GOOGLE_MAPS_API_KEY)

    def geocode(self):
        """
        Given the values in the record, run the geocoding if it has not already been done.
        """
        g = GoogleV3(api_key=settings.GOOGLE_MAPS_API_KEY)  # Our geocoding object
        if not self.is_geocoded:
            attempts = 0
            gdone = False
            if self.geocode_method == "forward":
                if self.google_place_id:
                    logger.debug("Attempting to do the geocode lookup by place_id...")
                    gresult = g.geocode(place_id=self.google_place_id)
                    attempts += 1
                    if gresult:
                        logger.debug("We received a result for place_id! Parsing...")
                        gdone = self.parse_geocoding_result(gresult)
                if not gdone:
                    logger.debug(
                        "Attempting to geocode based on entered address with value '{}'...".format(
                            self.formatted_address
                        )
                    )
                    gresult = g.geocode(
                        exactly_one=True, query=self.formatted_address
                    )  # Do query based on the entered address.
                    attempts += 1
                    if gresult:
                        logger.debug("We received a result for address! Parsing...")
                        gdone = self.parse_geocoding_result(gresult)
            else:
                logger.debug(
                    "Doing a reverse geocode for coordinates {}".format(self.latlong)
                )
                gresult = g.reverse(
                    exactly_one=True,
                    query=GPyPoint(self.latlong.coords[1], self.latlong.coords[0]),
                )  # Do reverse geocode.
                attempts += 1
                if gresult:
                    logger.debug("Received a result for the coordinates! Parsing...")
                    gdone = self.parse_geocoding_result(gresult)
            logger.debug(
                "Finished geocoding process with {} attempts made.".format(attempts)
            )
            self.geocode_attempts = F("geocode_attempts") + attempts
            self.save()

    def parse_geocoding_result(self, gresult):
        """
        Given a result from the geocoder, parse and interpret it.

        :param gresult: An instance of a result from a geopy geocoder.
        :returns: returns True or False to indicate success or failure
        """
        try:
            if self.geocode_method == "forward":
                self.latlong = Point(gresult.longitude, gresult.latitude)
            self.formatted_address = gresult.address
            raw_results = gresult.raw
            self.viewport_ne = Point(
                raw_results["geometry"]["viewport"]["northeast"]["lng"],
                raw_results["geometry"]["viewport"]["northeast"]["lat"],
            )
            self.viewport_sw = Point(
                raw_results["geometry"]["viewport"]["southwest"]["lng"],
                raw_results["geometry"]["viewport"]["southwest"]["lat"],
            )
            self.location_accuracy = raw_results["geometry"]["location_type"]
            if "place_id" in raw_results.keys() and raw_results["place_id"]:
                self.google_place_id = raw_results["place_id"]
            logger.debug(
                "Completed updating address and base geometry. Moving on to address components..."
            )
            for comp in raw_results["address_components"]:
                if "country" in comp["types"]:
                    self.country = comp["long_name"]
                    logger.debug("Set country to {}".format(self.country))
                if "postal_code" in comp["types"]:
                    self.postal_code = comp["long_name"]
                    logger.debug("Set postal code to {}".format(self.postal_code))
                if "administrative_area_level_1" in comp["types"]:
                    self.state = comp["long_name"]
                    logger.debug("Set state to {}".format(self.state))
                if "locality" in comp["types"]:
                    self.city = comp["long_name"]
                    logger.debug("Set city to {}".format(self.city))
        except KeyError as ke:  # pragma: no cover
            logger.error(
                "We tried to reference a key that was not in the result! Detailed error message was: {}".format(
                    ke
                )
            )
            return False
        except ValueError as ve:  # pragma: no cover
            logger.error(
                "We tried to assign an incompatible value from the result set to the db. Detailed error message was: {}".format(
                    ve
                )
            )
        logger.debug("Successfully parsed result!")
        return True
