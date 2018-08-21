from django.contrib import admin
from . import models


# Register your models here.
class GamerCommunityAdmin(admin.ModelAdmin):
    pass


class GamerProfileAdmin(admin.ModelAdmin):
    pass


class CommunityMembershipAdmin(admin.ModelAdmin):
    pass


class CommunityApplicationAdmin(admin.ModelAdmin):
    pass


class KickedUserAdmin(admin.ModelAdmin):
    pass


class BannedUserAdmin(admin.ModelAdmin):
    pass


class MutedUserAdmin(admin.ModelAdmin):
    pass


class BlockedUserAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.GamerCommunity, GamerCommunityAdmin)
admin.site.register(models.GamerProfile, GamerProfileAdmin)
admin.site.register(models.CommunityMembership, CommunityMembershipAdmin)
admin.site.register(models.CommunityApplication, CommunityApplicationAdmin)
admin.site.register(models.KickedUser, KickedUserAdmin)
admin.site.register(models.BannedUser, BannedUserAdmin)
admin.site.register(models.MutedUser, MutedUserAdmin)
admin.site.register(models.BlockedUser, BlockedUserAdmin)
