from django.contrib import admin
from .models import GamePublisher, GameSystem, PublishedGame, PublishedModule

# Register your models here.


class GamePublisherAdmin(admin.ModelAdmin):
    ordering = ['name']


class GameSystemAdmin(admin.ModelAdmin):
    pass


class PublishedGameAdmin(admin.ModelAdmin):
    list_display = ('title', 'edition', 'game_system', 'publisher')
    date_hierarchy = 'publication_date'


class PublishedModuleAdmin(admin.ModelAdmin):
    pass


admin.site.register(GamePublisher, GamePublisherAdmin)
admin.site.register(GameSystem, GameSystemAdmin)
admin.site.register(PublishedGame, PublishedGameAdmin)
admin.site.register(PublishedModule, PublishedModuleAdmin)
