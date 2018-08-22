from django.db import models
from model_utils.models import TimeStampedModel
from allauth.socialaccount.models import SocialAccount, SocialToken
from ..game_catalog.utils import AbstractUUIDModel
from ..gamer_profiles.models import GamerCommunity, GamerProfile
# Create your models here.


class DiscordServer(TimeStampedModel, AbstractUUIDModel):
    '''
    Discord server instance as gathered by record.
    '''
    discord_id = models.BigIntegerField()
    name = models.CharField(max_length=100)
    icon_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.discord_id)


class GamerDiscordLink(TimeStampedModel, AbstractUUIDModel):
    '''
    An abstraction that allows us to keep a record of synced
    M2M releationships with discord servers.
    '''
    gamer = models.OneToOneField(GamerProfile, on_delete=models.CASCADE, related_name='discord')
    socialaccount = models.OneToOneField(SocialAccount, on_delete=models.CASCADE, related_name='discord_link')
    servers = models.ManyToManyField(DiscordServer, related_name='gamers')

    def __str__(self):
        return "Server link for {}".format(self.gamer.username)

    def get_social_token(self):
        pass


class CommunityDiscordLink(TimeStampedModel, AbstractUUIDModel):
    '''
    An abstraction for communities to be linked to discord to track syncing.
    '''
    community = models.OneToOneField(GamerCommunity, on_delete=models.CASCADE, related_name='discord')
    servers = models.ManyToManyField(DiscordServer, related_name='communities')

    def __str__(self):
        return "Server link for community {}".format(self.community.name)
