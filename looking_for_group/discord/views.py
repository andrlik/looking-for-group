from allauth.socialaccount.providers.discord.views import DiscordOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView, OAuth2CallbackView
from .provider import DiscordProviderWithGuilds
# Create your views here.


class DiscordGuildOAuth2Adapater(DiscordOAuth2Adapter):
    '''
    Override adapter for local provider.
    '''
    provider_id = DiscordProviderWithGuilds.id


oauth2_login = OAuth2LoginView.adapter_view(DiscordGuildOAuth2Adapater)
oauth2_callback = OAuth2CallbackView.adapter_view(DiscordGuildOAuth2Adapater)
