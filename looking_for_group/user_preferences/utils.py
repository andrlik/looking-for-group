import logging

from django.core.cache import cache

from ..discord import models as discord_models
from ..game_catalog import models as catalog_models
from ..gamer_profiles import models as social_models
from ..games import models as game_models

logger = logging.getLogger("games")


def prime_site_stats_cache():
    """
    Collect stats for site and prime the cache. Run this as a scheduled task to
    improve performance.
    """
    logging.debug("Starting scheduled cache priming...")
    cache.set("site_total_communities", social_models.GamerCommunity.objects.count())
    cache.set("site_total_gamers", social_models.GamerProfile.objects.count())
    cache.set(
        "site_total_active_games",
        game_models.GamePosting.objects.exclude(
            status__in=["cancel", "closed"]
        ).count(),
    )
    cache.set(
        "site_total_completed_sessions",
        game_models.GameSession.objects.filter(status="complete").count(),
    )
    cache.set("site_total_systems", catalog_models.GameSystem.objects.count())
    cache.set("site_total_tracked_editions", catalog_models.GameEdition.objects.count())
    cache.set("site_total_publishers", catalog_models.GamePublisher.objects.count())
    cache.set("site_total_modules", catalog_models.PublishedModule.objects.count())
    cache.set("site_total_sourcebooks", catalog_models.SourceBook.objects.count())
    fetch_or_set_discord_comm_links()
    logging.debug("Finished cache priming.")


def fetch_or_set_discord_comm_links():
    """
    Tries to fetch count of discord community links from cache, and if not found
    retrieves the data, sets it in the cache, and then returns the result.
    """
    logger.debug("Starting discord community cache check...")
    discord_comm_links = cache.get("site_total_discord_communities")
    if not discord_comm_links:
        logger.debug("Discord count is stale, calculating...")
        discord_comm_links = 0
        dis_servers = discord_models.DiscordServer.objects.all()
        if dis_servers.count() > 0:
            comm_qs = None
            for server in dis_servers:
                if not comm_qs:
                    comm_qs = server.communities.all()
                else:
                    comm_qs = comm_qs.union(server.communities.all())
            if comm_qs:
                discord_comm_links = len(comm_qs)
            else:
                discord_comm_links = 0
        logger.debug("Saving discord community count to cache...")
        cache.set("site_total_discord_communities", discord_comm_links)
    logger.debug("Returning discord community count of {}".format(discord_comm_links))
    return discord_comm_links
