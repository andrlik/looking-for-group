from allauth.socialaccount.models import SocialAccount
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from ..game_catalog.utils import AbstractUUIDModel
from ..gamer_profiles.models import COMMUNITY_ROLES, GamerCommunity, GamerProfile

# Create your models here.

SYNC_STATUS_CHOICES = (
    ('synced', _('Synced')),
    ('syncing', _('Syncing in progress')),
    ('pending', _('Pending syncronization')),
)


class DiscordServer(TimeStampedModel, AbstractUUIDModel):
    '''
    Discord server instance as gathered by record.
    '''
    discord_id = models.CharField(max_length=250, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    icon_url = models.URLField(null=True, blank=True, help_text=_('Link to discord CDN hossted icon.'))

    def __str__(self):
        return "{} ({})".format(self.name, self.discord_id)


class GamerDiscordLink(TimeStampedModel, AbstractUUIDModel):
    '''
    An abstraction that allows us to keep a record of synced
    M2M releationships with discord servers.
    '''
    gamer = models.OneToOneField(GamerProfile, on_delete=models.CASCADE, related_name='discord')
    socialaccount = models.OneToOneField(SocialAccount, on_delete=models.CASCADE, related_name='discord_link')
    servers = models.ManyToManyField(DiscordServer, through='DiscordServerMembership', through_fields=('gamer_link', 'server'), related_name='gamers')
    sync_status = models.CharField(max_length=25, choices=SYNC_STATUS_CHOICES, default='pending', help_text=_('Sync status with discord.'))
    last_successful_sync = models.DateTimeField(null=True, blank=True, help_text=_('Last time sync successfully completed.'))

    def __str__(self):
        return "Server link for {}".format(self.gamer.username)

    def get_server_discord_id_list(self):
        result_list = []
        for server in self.servers.all():
            result_list.append(server.discord_id)
        return result_list


class DiscordServerMembership(TimeStampedModel, AbstractUUIDModel):
    '''
    Adds role to the relationships.
    '''
    server = models.ForeignKey(DiscordServer, on_delete=models.CASCADE)
    gamer_link = models.ForeignKey(GamerDiscordLink, on_delete=models.CASCADE)
    server_role = models.CharField(max_length=25, choices=COMMUNITY_ROLES)


class CommunityDiscordLink(TimeStampedModel, AbstractUUIDModel):
    '''
    An abstraction for communities to be linked to discord to track syncing.
    '''
    community = models.OneToOneField(GamerCommunity, on_delete=models.CASCADE, related_name='discord')
    servers = models.ManyToManyField(DiscordServer, related_name='communities')

    def __str__(self):
        return "Server link for community {}".format(self.community.name)
