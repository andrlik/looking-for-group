from django.contrib import admin
from .models import GamePublisher, GameSystem, PublishedGame, PublishedModule

# Register your models here.


class GamePublisherAdmin(admin.ModelAdmin):
    pass


class GameSystemAdmin(admin.ModelAdmin):
    pass


class PublishedGameAdmin(admin.ModelAdmin):
    pass


class PublishedModuleAdmin(admin.ModelAdmin):
    pass


admin.register(GamePublisher, GamePublisherAdmin)
admin.register(GameSystem, GameSystemAdmin)
admin.register(PublishedGame, PublishedGameAdmin)
admin.register(PublishedModule, PublishedModuleAdmin)
