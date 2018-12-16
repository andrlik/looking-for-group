from django.contrib import admin

from .models import Preferences

# Register your models here.


class PrefAdmin(admin.ModelAdmin):
    list_display = ['gamer', 'news_emails', 'notification_digest', 'feedback_volunteer']
    list_filter = ['news_emails', 'notification_digest', 'feedback_volunteer']


admin.site.register(Preferences, PrefAdmin)
