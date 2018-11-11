import logging

from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from .models import GamerDiscordLink
from .signals import updated_discord_social_account
from .tasks import prune_servers, sync_discord_servers_from_discord_account

logger = logging.getLogger('discord')


@receiver(social_account_added, sender=SocialLogin)
@receiver(social_account_updated, sender=SocialLogin)
def check_signal_from_allauth(sender, request, sociallogin, *args, **kwargs):
    logger.debug('Evaluating social account provider')
    if sociallogin.account.provider == "discord_with_guilds" and request.user.is_authenticated:  # pragma: no cover
        logger.debug("Discord account! Sending signal.")
        updated_discord_social_account.send(sender=SocialAccount, gamer=request.user.gamerprofile, socialaccount=sociallogin.account)


@receiver(updated_discord_social_account, sender=SocialAccount)
def create_or_update_server_list(sender, gamer, socialaccount, test_response=None, *args, **kwargs):
    logger.debug('Sending async task to update gamer servers.')
    gamer_discord, created = GamerDiscordLink.objects.get_or_create(
        gamer=gamer, socialaccount=socialaccount
    )
    gamer_discord.sync_status = 'pending'
    gamer_discord.save()
    async_task(sync_discord_servers_from_discord_account, gamer, socialaccount, test_response=test_response)


@receiver(post_delete, sender=SocialAccount)
def remove_discord_links(sender, instance, *args, **kwargs):
    logger.debug('signal evaluation social account provider')
    if instance.provider == "discord_with_guilds":  # pragma: no cover
        logger.debug('Sending async task to prune servers.')
        async_task(prune_servers)


@receiver(post_save, sender=SocialAccount)
def create_initial_link(sender, instance, created, *args, **kwargs):
    if created and "discord" in instance.provider:
        link = GamerDiscordLink.objects.get_or_create(gamer=instance.user.gamerprofile, socialaccount=instance)
        async_task(sync_discord_servers_from_discord_account, instance.user.gamerprofile, instance)