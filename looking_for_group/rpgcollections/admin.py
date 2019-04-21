from django.contrib import admin
from . import models

# Register your models here.


class GameLibraryAdmin(admin.ModelAdmin):
    pass


class BookAdmin(admin.ModelAdmin):
    list_display = ["library", "content_object", "in_print", "in_pdf", "created", "modified"]
    ordering = ["created"]


admin.site.register(models.GameLibrary, GameLibraryAdmin)
admin.site.register(models.Book, BookAdmin)
