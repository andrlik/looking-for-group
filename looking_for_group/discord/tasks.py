import logging
import requests
from allauth.socialaccount.models import SocialToken
from ..gamer_profiles.models import CommunityMembership
from .models import DiscordServer, GamerDiscordLink
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


def sync_discord_servers_from_discord_account(request, socialaccount):
    """
    Takes the gamer indicated and uses the discord account, to retrieve related
    servers. Calls an async task to prune servers afterwards before exiting.

    :param gamer: An instance of :class:`looking_for_group.gamer_profiles.models.GamerProfile`
    :param socialaccount: An instance of :class:`allauth.socialaccount.models.SocialAccount`

    :returns: A dict of results containing counts of servers linked, servers unlinked, new servers created.
    """
    if request.user.is_authenticated:
        new_links = 0
        unlinks = 0
        new_servers = 0
        new_memberships = 0
        memberships_updated = 0
        gamer = request.user.gamerprofile
        stokens = SocialToken.objects.filter(account=socialaccount).order_by(
            "-expires_at"
        )
        if stokens:
            logger.debug("Found a valid social token. Proceeding.")
            stoken = stokens[0]
            gamer_discord, created = GamerDiscordLink.objects.get_or_create(
                gamer=gamer, socialaccount=socialaccount
            )
            current_servers = gamer_discord.servers.all()
            updated_servers = []
            discord_adapter = DiscordGuildOAuth2Adapater()
            guild_list = discord_adapter.get_guilds_with_permissions(
                request, socialaccount.app, stoken
            )
            guild_dict = {}
            for guild in guild_list:
                iconurl = "https://cdn.discordapp.com/icons/{0}/{1}.png".format(
                    guild["id"], guild["icon"]
                )
                server, created = DiscordServer.objects.get_or_create(
                    discord_id=guild["id"],
                    defaults={"name": guild, "icon_url": iconurl},
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
            for server in list(current_servers):
                if server not in updated_servers:
                    gamer_discord.servers.remove(server)
                    unlinks += 1
            for server in updated_servers:
                if server not in current_servers:
                    gamer_discord.servers.add(server)
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
                    if membership.community_role != guild_dict[server.pk]:
                        membership.community_role = guild_dict[server.pk]
                        membership.save()
                        memberships_updated += 1
        else:
            logger.debug("No valid social token found, skipping.")
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
        return new_links, unlinks, new_servers, new_memberships, memberships_updated
    return False
