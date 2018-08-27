import logging
import requests
from django_q.tasks import async_task
from allauth.socialaccount.models import SocialToken
from ..gamer_profiles.models import CommunityMembership
from .models import DiscordServer, GamerDiscordLink, DiscordServerMembership
from .views import DiscordGuildOAuth2Adapater


logger = logging.getLogger("discord")


def prune_servers(pretend=False):
    """
    Queries all servers that have no gamers or communities
    linked to them. Unless pretend is true, deletes them all.
    Otherwise, only returns their number.

    :param pretend:
        Whether to treat this call as a dry-run.

    :returns: An int representing the number of servers pruned.
    """
    servers = DiscordServer.objects.exclude(gamers__isnull=False).exclude(
        communities__isnull=False
    )
    delete_count = servers.count()
    if pretend:
        logger.debug("Pretend mode: Would have deleted {} records".format(delete_count))
        return delete_count
    logger.info(
        "Preparing to prune unused discord servers, will log all records to debug."
    )
    for server in servers:
        logger.debug(
            "Deleting server {} with discord id of {}".format(
                server.name, server.discord_id
            )
        )
        server.delete()
    logger.info("Pruned {} discord servers.".format(delete_count))
    return delete_count


def sync_discord_servers_from_discord_account(gamerprofile, socialaccount, test_response=None):
    """
    Takes the gamer indicated and uses the discord account, to retrieve related
    servers. Calls an async task to prune servers afterwards before exiting.

    :param gamer: An instance of :class:`looking_for_group.gamer_profiles.models.GamerProfile`
    :param socialaccount: An instance of :class:`allauth.socialaccount.models.SocialAccount`

    :returns: 5 ints new servers linked, servers unlinked, new servers created, new memberships added
    and memberships updated.
    """
    logger.debug("Valid user")
    new_links = 0
    unlinks = 0
    new_servers = 0
    new_memberships = 0
    memberships_updated = 0
    gamer = gamerprofile
    stokens = SocialToken.objects.filter(account=socialaccount).order_by(
        "-expires_at"
    )
    if stokens:
        logger.debug("Found a valid social token. Proceeding.")
        stoken = stokens[0]
        gamer_discord, created = GamerDiscordLink.objects.get_or_create(
            gamer=gamer, socialaccount=socialaccount
        )
        current_servers = gamer_discord.get_server_discord_id_list()
        logger.debug("Current servers are: {}".format(current_servers))
        updated_servers = []
        # We create a dummy request here since we can't pickle it.
        request = requests.get('/sync/guilds/')
        discord_adapter = DiscordGuildOAuth2Adapater(request)
        if test_response:
            guild_list = discord_adapter.get_guilds_with_permissions(stoken.app, stoken, test_response=test_response)
        else:
            guild_list = discord_adapter.get_guilds_with_permissions(stoken.app, stoken)  # pragma: no cover
        # We will use this dict to provide quick reference for community roles.
        guild_dict = {}
        for guild in guild_list:
            iconurl = "https://cdn.discordapp.com/icons/{0}/{1}.png".format(
                guild["id"], guild["icon"]
            )
            server, created = DiscordServer.objects.get_or_create(
                discord_id=guild["id"],
                defaults={"name": guild["name"], "icon_url": iconurl},
            )
            if created:
                new_servers += 1
            # Update name and icon if different
            guild_dict[server.pk] = guild["comm_role"]
            if server.name != guild["name"] or server.icon_url != iconurl:
                server.name = guild["name"]
                server.icon_url = iconurl
                server.save()
            updated_servers.append(server)
        logger.debug("Updated servers are: {}".format(updated_servers))
        for server in gamer_discord.servers.all():
            if server not in updated_servers:
                logger.debug(
                    "Server with discord_id {} is no longer valid, unlinking...".format(
                        server.discord_id
                    )
                )
                DiscordServerMembership.objects.get(
                    gamer_link=gamer_discord, server=server
                ).delete()
                unlinks += 1
        for server in updated_servers:
            if server.discord_id not in current_servers:
                logger.debug(
                    "Server with discord_id {} is not currently linked to gamer. Linking...".format(
                        server.discord_id
                    )
                )
                DiscordServerMembership.objects.create(
                    server=server,
                    gamer_link=gamer_discord,
                    server_role=guild_dict[server.pk],
                )
                new_links += 1
        gamer_discord.refresh_from_db()
        servers_with_comms = gamer_discord.servers.exclude(communities__isnull=True)
        for server in servers_with_comms:
            community_links = server.communities.all()
            for clink in community_links:
                membership, created = CommunityMembership.objects.get_or_create(
                    community=clink.community,
                    gamer=gamer,
                    defaults={"community_role": guild_dict[server.pk]},
                )
                if created:
                    new_memberships += 1
                # We only update the role if the new role is higher than the one they currently have.
                logger.debug(
                    "Comparing current role {0} to {1}".format(
                        membership.community_role, guild_dict[server.pk]
                    )
                )
                if membership.community_role != guild_dict[
                        server.pk
                ] and membership.less_than(guild_dict[server.pk]):
                    logger.debug(
                        "Roles do not match and the discord role is higher than our current role"
                    )
                    membership.community_role = guild_dict[server.pk]
                    membership.save()
                    memberships_updated += 1
    logger.info(
        "Updated discord records for gamer {0}. Linked {1} servers, unlinked {2} servers, created {3} new servers, added {4} new memberships, and updated {5} existing memberships.".format(
            gamer.username,
            new_links,
            unlinks,
            new_servers,
            new_memberships,
            memberships_updated,
        )
    )
    if unlinks:
        # Since we've unlinked, let's practice good housekeeping and prune any
        # unneeded servers.
        async_task(prune_servers)
    return new_links, unlinks, new_servers, new_memberships, memberships_updated
