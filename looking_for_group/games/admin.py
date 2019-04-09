from django.contrib import admin

from . import models

# Register your models here.


class GamePostingAdmin(admin.ModelAdmin):
    pass


class GameSessionAdmin(admin.ModelAdmin):
    pass


class PlayerAdmin(admin.ModelAdmin):
    pass


class CharacterAdmin(admin.ModelAdmin):
    pass


class AdventureLogAdmin(admin.ModelAdmin):
    pass


class GameApplicantAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.GamePosting, GamePostingAdmin)
admin.site.register(models.GameSession, GameSessionAdmin)
admin.site.register(models.AdventureLog, AdventureLogAdmin)
admin.site.register(models.Player, PlayerAdmin)
admin.site.register(models.Character, CharacterAdmin)
admin.site.register(models.GamePostingApplication, GameApplicantAdmin)
