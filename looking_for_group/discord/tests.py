from allauth.socialaccount.providers.discord.tests import DiscordTests
from .provider import DiscordProviderWithGuilds
# Create your tests here.


class DiscordGuildTests(DiscordTests):
    provider_id = DiscordProviderWithGuilds.id
