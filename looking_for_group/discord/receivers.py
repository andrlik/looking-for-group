import logging
from django.dispatch import receiver
from django_q.tasks import async_task
from django.db.models.signals import post_delete
from allauth.socialaccount.signals import social_account_added, social_account_updated
from allauth.socialaccount.models import SocialLogin, SocialAccount
from .tasks import prune_servers, sync_discord_servers_from_discord_account
from .signals import updated_discord_social_account

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
    async_task(sync_discord_servers_from_discord_account, gamer, socialaccount, test_response=test_response)


@receiver(post_delete, sender=SocialAccount)
def remove_discord_links(sender, instance, *args, **kwargs):
    logger.debug('signal evaluation social account provider')
    if instance.provider == "discord_with_guilds":  # pragma: no cover
        logger.debug('Sending async task to prune servers.')
        async_task(prune_servers)