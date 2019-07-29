from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _


class WorldBorder(models.Model):
    name = models.CharField(max_length=50)
    area = models.IntegerField()
    pop2005 = models.IntegerField(_("Population in 2005"))
    fips = models.CharField(_("FIPS Code"), max_length=2)
    iso2 = models.CharField(_("2 Digit ISO"), max_length=2)
    iso3 = models.CharField(_("3 Digit ISO"), max_length=3)
    un = models.IntegerField(_("United Nations Code"))
    region = models.IntegerField(_("Region Code"))
    subregion = models.IntegerField(_("Subregion Code"))
    lon = models.FloatField()
    lat = models.FloatField()

    mpoly = models.MultiPolygonField()

    def __str__(self):
        return self.name
