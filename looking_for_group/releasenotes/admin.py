from django.contrib import admin

from .models import ReleaseNote, ReleaseNotice
from .utils import load_release_notes_from_file

# Register your models here.


def update_release_notes_from_source(modeladmin, request, queryset=None):
    load_release_notes_from_file()


update_release_notes_from_source.short_description = (
    "Update release notes from the master changelog file specified in SETTINGS"
)


@admin.register(ReleaseNote)
class ReleaseNoteAdmin(admin.ModelAdmin):
    """
    Admin object for Release Note instance.
    """

    list_display = ["version", "release_date"]
    date_hierarchy = "release_date"
    actions = [update_release_notes_from_source]


@admin.register(ReleaseNotice)
class ReleaseNoticeAdmin(admin.ModelAdmin):
    """
    Admin object for the Release Notice instance.
    """

    list_display = ["user", "latest_version_shown"]
    ordering = ["user__username"]
