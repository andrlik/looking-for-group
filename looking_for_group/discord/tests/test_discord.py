from test_plus import TestCase
from django.contrib.sites.models import Site
from allauth.tests import MockedResponse, TestCase as AllAuthTestCase
from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount import providers
from ...gamer_profiles.tests import factories
from ..provider import DiscordProviderWithGuilds
from ..tasks import prune_servers
from .. import models
# Create your tests here.


class DiscordGuildTests(OAuth2TestsMixin, AllAuthTestCase):
    provider_id = DiscordProviderWithGuilds.id

    def get_mocked_response(self):
        return MockedResponse(200, """{
            "id": "80351110224678912",
            "username": "Nelly",
            "discriminator": "1337",
            "avatar": "8342729096ea3675442027381ff50dfe",
            "verified": true,
            "email": "nelly@example.com"
        }""")


class AbstractDiscordTest(TestCase):
    '''
    Abstract test case to make setup more replicable.
    '''

    def setUp(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.community1 = factories.GamerCommunityFactory(owner=self.gamer1)
        self.gamer3 = factories.GamerProfileFactory()
        self.discord_server1 = models.DiscordServer.objects.create(discord_id="80351110224678912", name="1337 Krew", icon_url="https://cdn.discordapp.com/icons/80351110224678912/8342729096ea3675442027381ff50dfe.png")
        self.discord_server2 = models.DiscordServer.objects.create(discord_id="80351110224678945", name="Oily Boyz", icon_url="https://cdn.discordapp.com/icons/80351110224678945/8342729096ea3675442027381ff50dfe.png")
        self.discord_server3 = models.DiscordServer.objects.create(discord_id="80351110224678952", name="Nest of Vipers", icon_url="https://cdn.discordapp.com/icons/80351110224678952/8342729096ea3675442027381ff50dfe.png")
        self.comm_link = models.CommunityDiscordLink.objects.create(community=self.community1)
        self.comm_link.servers.add(self.discord_server3)
        self.comm_link.servers.add(self.discord_server2)
        provider = providers.registry.by_id("discord_with_guilds")
        self.app = SocialApp.objects.create(provider=provider.id, name=provider.id, client_id='jkdjlskjsdljsdf', key=provider.id, secret='dummy')
        self.app.sites.add(Site.objects.get_current())
        self.socialaccount = SocialAccount.objects.create(user=self.gamer1.user, provider="discord_with_guilds")
        self.stoken = SocialToken.objects.create(app=self.app, account=self.socialaccount, token="jlkdjlsjldsjdfsjslkdj", token_secret="jkdjlsdjldfkj", expires_at=None)


class DiscordServerPruneTest(AbstractDiscordTest):
    '''
    Test prune method.
    '''

    def test_prune_with_two_communities(self):
        check_number = prune_servers()
        assert check_number == 1
        assert models.DiscordServer.objects.count() == 2

    def test_pretend_with_two_communities(self):
        check_number = prune_servers(pretend=True)
        assert check_number == 1
        assert models.DiscordServer.objects.count() == 3

    def test_prune_with_one_community_and_one_user(self):
        gamerlink = models.GamerDiscordLink.objects.create(gamer=self.gamer1, socialaccount=self.socialaccount)
        gamerlink.servers.add(self.discord_server1)
        self.comm_link.servers.remove(self.discord_server3)
        check_num = prune_servers()
        assert check_num == 1
        assert models.DiscordServer.objects.count() == 2

    def test_prune_with_one_community_only(self):
        self.comm_link.servers.remove(self.discord_server3)
        check_num = prune_servers()
        assert check_num == 2
        assert models.DiscordServer.objects.count() == 1

    def test_prune_with_no_links(self):
        self.comm_link.servers.remove(self.discord_server2, self.discord_server3)
        check_num = prune_servers()
        assert check_num == 3
        assert models.DiscordServer.objects.count() == 0
