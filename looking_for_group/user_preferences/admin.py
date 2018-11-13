from django.contrib import admin
from .models import Preferences
# Register your models here.


class PrefAdmin(admin.ModelAdmin):
    list_display = ['gamer']


admin.site.register(Preferences, PrefAdmin)
