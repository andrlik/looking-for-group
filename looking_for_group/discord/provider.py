from allauth.socialaccount.providers.discord.provider import DiscordProvider, DiscordAccount


class DiscordGuildAccount(DiscordAccount):
    pass


class DiscordProviderWithGuilds(DiscordProvider):
    '''
    Adds the guild scope to the Oauth request.
    '''
    id = 'discord_with_guilds'
    name = 'Discord'
    account_class = DiscordGuildAccount

    def get_default_scope(self):
        return ['email', 'identify', 'guilds']  # pragma: no cover


provider_classes = [DiscordProviderWithGuilds, ]
