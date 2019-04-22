from django.contrib import admin

from . import models

# Register your models here.


class ServerAdmin(admin.ModelAdmin):
    pass


class GamerLinkAdmin(admin.ModelAdmin):
    list_display = ['gamer', 'sync_status', 'last_successful_sync']
    ordering = ['gamer__username']


class CommLinkAdmin(admin.ModelAdmin):
    pass


class ServerMembership(admin.ModelAdmin):
    list_display = ['server', 'gamer_link', 'server_role']
    ordering = ['server__name', 'created']


admin.site.register(models.DiscordServer, ServerAdmin)
admin.site.register(models.GamerDiscordLink, GamerLinkAdmin)
admin.site.register(models.CommunityDiscordLink, CommLinkAdmin)
admin.site.register(models.DiscordServerMembership, ServerMembership)
