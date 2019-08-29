from django.contrib.gis import admin

from .models import Location

# Register your models here.


class LocationAdmin(admin.ModelAdmin):
    pass


admin.site.register(Location, LocationAdmin)
