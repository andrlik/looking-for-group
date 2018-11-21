from django.contrib import admin

from .models import MOTD

# Register your models here.


class MOTDAdmin(admin.ModelAdmin):
    list_display = ['message', 'enabled', 'timebased', 'start', 'end']
    list_filter = ['enabled', 'timebased']


admin.site.register(MOTD, MOTDAdmin)
