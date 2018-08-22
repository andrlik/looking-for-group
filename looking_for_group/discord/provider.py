from allauth.socialaccount.providers.discord.provider import DiscordProvider

class DiscordProviderWithGuilds(DiscordProvider):
    '''
    Adds the guild scope to the Oauth request.
    '''
    id = 'discord_with_guilds'

    def get_default_scope(self):
        return ['email', 'identify', 'guilds']  # pragma: no cover

provider_classes = [DiscordProviderWithGuilds]
