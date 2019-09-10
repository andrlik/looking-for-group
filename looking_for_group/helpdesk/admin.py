from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import IssueCommentLink, IssueLink
from .utils import get_backend_client

# Register your models here.


def sync_from_source(modeladmin, request, queryset):
    gl = get_backend_client()
    for x in queryset:
        x.sync_with_source(backend_object=gl)


sync_from_source.short_description = _("Sync issue data from remote repository")


class IssueLinkAdmin(admin.ModelAdmin):
    list_display = [
        "external_id",
        "creator",
        "cached_title",
        "cached_status",
        "created",
        "sync_status",
        "last_sync",
    ]
    actions = [sync_from_source]


class IssueCommentLinkAdmin(admin.ModelAdmin):
    list_display = ["master_issue", "creator", "created", "sync_status", "last_sync"]
    actions = [sync_from_source]


admin.site.register(IssueLink, IssueLinkAdmin)
admin.site.register(IssueCommentLink, IssueCommentLinkAdmin)
