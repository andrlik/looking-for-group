from django.contrib import admin

from .models import GamePublisher, GameSystem, PublishedGame, PublishedModule, GameEdition, SourceBook

# Register your models here.


class GamePublisherAdmin(admin.ModelAdmin):
    ordering = ['name']


class GameSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'original_publisher')
    list_select_related = ('original_publisher', )
    ordering = ['name', '-publication_date']


class PublishedGameAdmin(admin.ModelAdmin):
    list_display = ('title',)
    date_hierarchy = 'publication_date'
    ordering = ['title']
    search_fields = ['title']


class EditionAdmin(admin.ModelAdmin):
    list_display = ('game', 'name', 'game_system', 'publisher', 'release_date')
    date_hierarchy = 'release_date'
    list_filter = ('game', 'game_system', 'publisher')
    search_fields = ['game__title', 'name']
    ordering = ['game__title', '-release_date']


class SourceBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'edition', 'edition', 'corebook', 'release_date')
    date_hierarchy = 'release_date'
    list_filter = ('edition', 'corebook')
    search_fields = ['title']


class PublishedModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent_game', 'publisher')
    date_hierarchy = 'publication_date'
    ordering = ['title', '-publication_date']
    search_fields = ['title']
    list_filter = ('parent_game', )
    list_select_related = ('publisher', 'parent_game')


admin.site.register(GamePublisher, GamePublisherAdmin)
admin.site.register(GameSystem, GameSystemAdmin)
admin.site.register(PublishedGame, PublishedGameAdmin)
admin.site.register(PublishedModule, PublishedModuleAdmin)
admin.site.register(GameEdition, EditionAdmin)
admin.site.register(SourceBook, SourceBookAdmin)
