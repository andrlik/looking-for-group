from datetime import timedelta

import factory.django
from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin, SocialToken
from allauth.socialaccount.signals import social_account_added, social_account_updated
from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import MockedResponse
from allauth.tests import TestCase as AllAuthTestCase
from allauth.tests import mocked_response
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.test import TransactionTestCase
from django.test.client import RequestFactory
from django.utils import timezone

from .. import models
from ...gamer_profiles.tests import factories
from ..provider import DiscordProviderWithGuilds
from ..signals import updated_discord_social_account
from ..tasks import find_discord_orphans, orphan_discord_sync, prune_servers, sync_discord_servers_from_discord_account
from ..views import DiscordGuildOAuth2Adapater

# Create your tests here.


@factory.django.mute_signals(updated_discord_social_account)
class DiscordGuildTests(OAuth2TestsMixin, AllAuthTestCase):
    provider_id = DiscordProviderWithGuilds.id

    def get_mocked_response(self):
        return MockedResponse(
            200,
            """{
            "id": "80351110224678912",
            "username": "Nelly",
            "discriminator": "1337",
            "avatar": "8342729096ea3675442027381ff50dfe",
            "verified": true,
            "email": "nelly@example.com"
        }""",
        )


class AbstractDiscordTest(TransactionTestCase):
    """
    Abstract test case to make setup more replicable.
    """

    def setUp(self):
        self.gamer1 = factories.GamerProfileFactory()
        self.gamer2 = factories.GamerProfileFactory()
        self.gamer3 = factories.GamerProfileFactory()
        self.community1 = factories.GamerCommunityFactory(
            owner=factories.GamerProfileFactory()
        )
        self.discord_server1 = models.DiscordServer.objects.create(
            discord_id="80351110224678912",
            name="1337 Krew",
            icon_url="https://cdn.discordapp.com/icons/80351110224678912/8342729096ea3675442027381ff50dfe.png",
        )
        self.discord_server2 = models.DiscordServer.objects.create(
            discord_id="80351110224678945",
            name="Oily Boyz",
            icon_url="https://cdn.discordapp.com/icons/80351110224678945/8342729096ea3675442027381ff50dfe.png",
        )
        self.discord_server3 = models.DiscordServer.objects.create(
            discord_id="80351110224678952",
            name="Nest of Vipers",
            icon_url="https://cdn.discordapp.com/icons/80351110224678952/8342729096ea3675442027381ff50dfe.png",
        )
        self.comm_link = models.CommunityDiscordLink.objects.get(
            community=self.community1
        )
        self.community2 = factories.GamerCommunityFactory(owner=self.gamer2)
        self.comm_link.servers.add(self.discord_server3)
        self.comm_link.servers.add(self.discord_server2)
        provider = providers.registry.by_id("discord_with_guilds")
        self.app = SocialApp.objects.create(
            provider=provider.id,
            name=provider.id,
            client_id="jkdjlskjsdljsdf",
            key=provider.id,
            secret="dummy",
        )
        self.app.sites.add(Site.objects.get_current())
        self.socialaccount = SocialAccount.objects.create(
            user=self.gamer1.user, provider="discord_with_guilds"
        )
        with factory.django.mute_signals(post_save):
            self.stoken = SocialToken.objects.create(
                app=self.app,
                account=self.socialaccount,
                token="jlkdjlsjldsjdfsjslkdj",
                token_secret="jkdjlsdjldfkj",
                expires_at=timezone.now() + timedelta(days=30),
            )


class AllAuthAbstractDiscordTestCase(AbstractDiscordTest, AllAuthTestCase):
    pass


class DiscordOrphanTest(AbstractDiscordTest):
    """
    Tests our orphan tasks, first by supressing the post_save generation of GDLs.
    """

    def setUp(self):
        super().setUp()
        self.gamer4 = factories.GamerProfileFactory()
        self.g4a = SocialAccount.objects.create(
            user=self.gamer4.user, uid=123456789, provider="discord_with_guilds"
        )
        with factory.django.mute_signals(post_save):
            self.g4t = SocialToken.objects.create(
                app=self.app,
                account=self.g4a,
                token="jkdjsdlkjdslj",
                token_secret="kdjksljdlskjdlsfk",
                expires_at=timezone.now() + timedelta(days=30),
            )

    def test_orphan_discovery(self):
        assert find_discord_orphans() == 2

    def test_discord_sync_with_pending(self):
        assert find_discord_orphans() == 2
        assert orphan_discord_sync(pretend=True) == 2
        self.gamer4.discord.sync_status = "synced"
        self.gamer4.discord.last_successful_sync = timezone.now()
        self.gamer4.discord.save()
        assert orphan_discord_sync(pretend=True) == 1


class DiscordServerPruneTest(AbstractDiscordTest):
    """
    Test prune method.
    """

    def test_prune_with_two_communities(self):
        check_number = prune_servers()
        assert check_number == 1
        assert models.DiscordServer.objects.count() == 2

    def test_pretend_with_two_communities(self):
        check_number = prune_servers(pretend=True)
        assert check_number == 1
        assert models.DiscordServer.objects.count() == 3

    def test_prune_with_one_community_and_one_user(self):
        gamerlink = models.GamerDiscordLink.objects.create(
            gamer=self.gamer1, socialaccount=self.socialaccount
        )
        models.DiscordServerMembership.objects.create(
            server=self.discord_server3, gamer_link=gamerlink, server_role="member"
        )
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


class TestPermissionParsing(TransactionTestCase):
    """
    Ensure that discord permissions are being properly parsed into community roles.
    """

    def setUp(self):
        self.discord_adapater = DiscordGuildOAuth2Adapater(
            RequestFactory().get("/sync/guilds")
        )
        self.guild = {
            "id": "3190347389327895798",
            "name": "Happy Boyz",
            "icon": "7894702386702357jfkdl",
            "owner": False,
            "permissions": None,
        }
        self.admin_permission_list = [536879146, 738222127, 8, 209977352]
        self.moderator_permission_list = [209977376, 209985536, 8192, 32]
        self.member_permission_list = [103896065, 1312152641, 1312283713, 201579585]

    def test_admin_checks(self):
        self.guild["owner"] = True
        self.guild["permissions"] = 209977376
        assert self.discord_adapater.parse_permissions(self.guild) == "admin"
        self.guild["owner"] = False
        for perm in self.admin_permission_list:
            self.guild["permissions"] = perm
            assert self.discord_adapater.parse_permissions(self.guild) == "admin"

    def test_moderator_parsing(self):
        for perm in self.moderator_permission_list:
            self.guild["permissions"] = perm
            assert self.discord_adapater.parse_permissions(self.guild) == "moderator"

    def test_member_parsing(self):
        for perm in self.member_permission_list:
            self.guild["permissions"] = perm
            assert self.discord_adapater.parse_permissions(self.guild) == "member"


class TestDiscordServerRetrieval(AbstractDiscordTest):
    """
    Use a mocked response to test guild syncing.
    """

    def setUp(self):
        super().setUp()
        self.gamerlink = models.GamerDiscordLink.objects.create(
            gamer=self.gamer1, socialaccount=self.socialaccount
        )
        self.servermember = models.DiscordServerMembership.objects.create(
            gamer_link=self.gamerlink, server=self.discord_server2
        )
        self.servermember2 = models.DiscordServerMembership.objects.create(
            gamer_link=self.gamerlink, server=self.discord_server3
        )
        self.comm_link2 = models.CommunityDiscordLink.objects.get(
            community=self.community2
        )
        self.discord_server4 = models.DiscordServer.objects.create(
            discord_id="323789347983279238",
            name="I am new",
            icon_url="https://www.google.com",
        )
        self.comm_link2.servers.add(self.discord_server4)
        self.community2.add_member(self.gamer1, role="member")

    def get_mocked_response(self):
        return MockedResponse(
            200,
            """[{"id": "80351110224678912", "name": "1337 Krew", "icon": "8342729096ea3675442027381ff50dfe", "owner": true, "permissions": 536879146}, {"id": "80351110224678952", "name":"something new", "icon": "dsjf894u894rufw", "owner": false, "permissions": 209977376}, {"id": "323789347983279238", "name": "Renegade Grrlz", "icon": "743873289473289hhfjlkdsjsdl", "owner": false, "permissions": 209977376}, {"id": "87834278923782437893749", "name": "Brand new server", "icon": "798432jkjfhdhd", "owner": false, "permissions": 103896065}]""",
            {"content-type": "application/json"},
        )

    def get_empty_mock_response(self):
        return MockedResponse(200, """[]""", {"content-type": "application/json"})

    def test_server_pull(self):
        """
        Tests syncing with a mocked response.
        """
        dummy_request = RequestFactory().get("/sync/guilds")
        self.discord_adapater = DiscordGuildOAuth2Adapater(dummy_request)
        resp_mock = self.get_mocked_response()
        with mocked_response(resp_mock):
            resp = self.discord_adapater.get_guilds_with_permissions(
                app=self.stoken.app, token=self.stoken
            )
        assert len(resp) == 4
        for server in resp:
            assert "comm_role" in server.keys()
        assert resp[0]["comm_role"] == "admin"
        assert resp[1]["comm_role"] == "moderator"
        assert resp[2]["comm_role"] == "moderator"
        assert resp[3]["comm_role"] == "member"

    def test_run_sync(self):
        """
        Attempts to run a full sync.
        """
        resp_mock = self.get_mocked_response()
        self.client.force_login(user=self.gamer1.user)
        with mocked_response(resp_mock):
            new_links, unlinks, new_servers, new_memberships, memberships_updated = sync_discord_servers_from_discord_account(
                self.gamer1, self.socialaccount, test_response=resp_mock
            )
        assert new_links == 3
        assert unlinks == 1
        assert new_servers == 1
        assert new_memberships == 1
        assert memberships_updated == 1
        assert self.community2.get_role(self.gamer1) == "Moderator"


class TestSignals(AbstractDiscordTest):
    """
    Test the above with signals instead.
    """

    def setUp(self):
        super().setUp()
        self.gamerlink = models.GamerDiscordLink.objects.create(
            gamer=self.gamer1, socialaccount=self.socialaccount
        )
        self.servermember = models.DiscordServerMembership.objects.create(
            gamer_link=self.gamerlink, server=self.discord_server2
        )
        self.servermember2 = models.DiscordServerMembership.objects.create(
            gamer_link=self.gamerlink, server=self.discord_server3
        )
        self.comm_link2 = models.CommunityDiscordLink.objects.get(
            community=self.community2
        )
        self.discord_server4 = models.DiscordServer.objects.create(
            discord_id="323789347983279238",
            name="I am new",
            icon_url="https://www.google.com",
        )
        self.comm_link2.servers.add(self.discord_server4)
        self.community2.add_member(self.gamer1, role="member")
        self.factory = RequestFactory()

    def get_mocked_response(self):
        return MockedResponse(
            200,
            """[{"id": "80351110224678912", "name": "1337 Krew", "icon": "8342729096ea3675442027381ff50dfe", "owner": true, "permissions": 536879146}, {"id": "80351110224678952", "name":"something new", "icon": "dsjf894u894rufw", "owner": false, "permissions": 209977376}, {"id": "323789347983279238", "name": "Renegade Grrlz", "icon": "743873289473289hhfjlkdsjsdl", "owner": false, "permissions": 209977376}, {"id": "87834278923782437893749", "name": "Brand new server", "icon": "798432jkjfhdhd", "owner": false, "permissions": 103896065}]""",
            {"content-type": "application/json"},
        )

    def test_socialaccount_update(self):
        self.client.force_login(self.gamer1.user)
        resp_mock = self.get_mocked_response()
        with mocked_response(resp_mock):
            print("Sending test signal")
            updated_discord_social_account.send(
                sender=SocialAccount,
                gamer=self.gamer1,
                socialaccount=self.socialaccount,
                test_response=resp_mock,
            )
            print("Signal sent")
        self.gamerlink.refresh_from_db()
        assert self.gamerlink.servers.count() == 4

    # def test_social_account_added(self):
    #     self.client.force_login(self.gamer2.user)
    #     request = self.factory.get('/')
    #     request.user = self.gamer2.user
    #     resp_mock = self.get_mocked_response()
    #     with mocked_response(resp_mock):
    #         with factory.django.mute_signals(social_account_added, social_account_updated):
    #             sociallogin = SocialLogin(user=self.gamer2.user, account=SocialAccount.objects.create(user=self.gamer2.user, provider='discord_with_guilds', uid='jkdjsldkjdskljdslkj', extra_data={"username": "reaper"}))
    #             self.stoken = SocialToken.objects.create(
    #                 app=self.app,
    #                 account=sociallogin.account,
    #                 token="jlkdjlsjldsjdfsjslkdj",
    #                 token_secret="jkdjlsdjldfkj",
    #                 expires_at=None,
    #             )
    #         social_account_added.send(sender=SocialLogin, request=request, sociallogin=sociallogin)
    #     assert models.GamerDiscordLink.objects.count() == 2
    #     link_to_test = models.GamerDiscordLink.objects.get(gamer=self.gamer2)
    #     assert link_to_test.servers.count() == 4

    # def test_social_account_updated(self):
    #     self.client.force_login(self.gamer1.user)
    #     request = self.factory.get('/')
    #     request.user = self.gamer1.user
    #     sa = self.gamerlink.socialaccount
    #     resp_mock = self.get_mocked_response()
    #     with mocked_response(resp_mock):
    #         social_account_updated.send(sender=SocialLogin, request=request, sociallogin=SocialLogin(user=self.gamer1.user, account=sa))
    #     self.gamerlink.refresh_from_db()
    #     assert self.gamerlink.servers.count() ==
