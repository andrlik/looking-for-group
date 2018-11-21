from django.contrib import admin

from .models import Invite

# Register your models here.


class InviteAdmin(admin.ModelAdmin):
    list_display = ['label', 'content_object', 'creator', 'created', 'expires_at', 'status', 'accepted_by']
    ordering = ['-created']


admin.site.register(Invite, InviteAdmin)
