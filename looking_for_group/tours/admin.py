from django.contrib import admin

from . import models

# Register your models here.


class TourAdmin(admin.ModelAdmin):
    list_display = ["name", "enabled", "created", "modified"]


class StepAdmin(admin.ModelAdmin):
    list_display = ["tour", "step_order"]
    list_filter = ["tour"]


admin.site.register(models.Tour, TourAdmin)
admin.site.register(models.Step, StepAdmin)
