from django.contrib import admin
from .models import GamePublisher, GameSystem, PublishedGame, PublishedModule

# Register your models here.


class GamePublisherAdmin(admin.ModelAdmin):
    ordering = ['name']


class GameSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'original_publisher')
    list_select_related = ('original_publisher', )
    ordering = ['name', '-publication_date']


class PublishedGameAdmin(admin.ModelAdmin):
    list_display = ('title', 'edition', 'game_system', 'publisher')
    date_hierarchy = 'publication_date'
    ordering = ['title', '-publication_date']
    list_filter = ('publisher', )
    list_select_related = ('publisher', )
    search_fields = ['title']


class PublishedModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent_game', 'publisher', 'parent_game__game_system')
    date_hierarchy = 'publication_date'
    ordering = ['title', '-publication_date']
    search_fields = ['title']
    list_filter = ('parent_game', )
    list_select_related = ('publisher', 'parent_game')


admin.site.register(GamePublisher, GamePublisherAdmin)
admin.site.register(GameSystem, GameSystemAdmin)
admin.site.register(PublishedGame, PublishedGameAdmin)
admin.site.register(PublishedModule, PublishedModuleAdmin)
