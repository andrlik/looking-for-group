import requests
from allauth.socialaccount.providers.discord.views import DiscordOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView, OAuth2CallbackView
from .provider import DiscordProviderWithGuilds
from .permissions import Permissions
# Create your views here.


class DiscordGuildOAuth2Adapater(DiscordOAuth2Adapter):
    '''
    Override adapter for local provider.
    '''
    provider_id = DiscordProviderWithGuilds.id
    guilds_url = 'https://discordapp.com/api/users/@me/guilds'
    get_guild_url = 'https://discordapp.com/api/guilds'

    def get_guilds_with_permissions(self, app, token, test_response=None, **kwargs):
        '''
        Fetches the current user's guild listings.

        :returns: A python representation of the JSON list of discord guilds.
        '''
        headers = {
            'Authorization': 'Bearer {0}'.format(token.token),
            'Content-Type': 'application/json',
        }
        if test_response:
            guild_data = test_response.json()
        else:
            guild_data = requests.get(self.guilds_url, headers=headers).json()
        for guild in guild_data:
            guild['comm_role'] = self.parse_permissions(guild)
        return guild_data

    def parse_permissions(self, guild_dict):
        '''
        For a given permissions listing in a discord guild, evaluate whether
        the user is an admin or moderator and return the role.
        '''
        if guild_dict['owner']:
            return 'admin'
        permission_inspector = Permissions(guild_dict['permissions'])
        if permission_inspector.administrator:
            return 'admin'
        if permission_inspector.manage_messages or permission_inspector.manage_server:
            return 'moderator'
        return 'member'


oauth2_login = OAuth2LoginView.adapter_view(DiscordGuildOAuth2Adapater)
oauth2_callback = OAuth2CallbackView.adapter_view(DiscordGuildOAuth2Adapater)
