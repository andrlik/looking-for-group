from django.contrib import admin

from . import models

# Register your models here.


class MessageReportAdmin(admin.ModelAdmin):
    list_display = ['reporter', 'created', 'plaintiff', 'report_type', 'status']
    list_filter = ['status', 'report_type']
    ordering = ['-created', 'status']

    class Meta:
        model = models.MessageReport


class SilenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'ending']
    ordering = ['-ending']

    class Meta:
        model = models.SilencedUser


admin.site.register(models.MessageReport, MessageReportAdmin)
admin.site.register(models.SilencedUser, SilenceAdmin)
