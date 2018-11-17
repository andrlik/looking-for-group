import logging

from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.db import IntegrityError
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django_q.tasks import async_task

from ..users.models import User
from .models import GamerDiscordLink
from .signals import updated_discord_social_account
from .tasks import prune_servers, sync_discord_servers_from_discord_account

logger = logging.getLogger("discord")


@receiver(social_account_added, sender=SocialLogin)
@receiver(social_account_updated, sender=SocialLogin)
@receiver(user_signed_up, sender=User)
def check_signal_from_allauth(sender, request, *args, **kwargs):
    sociallogin = kwargs.pop("sociallogin", None)
    logger.debug("Evaluating social account provider")
    if (
        sociallogin
        and "discord" in sociallogin.account.provider
        and request.user.is_authenticated
    ):  # pragma: no cover
        logger.debug("Discord account! Sending signal.")
        updated_discord_social_account.send(
            sender=SocialAccount,
            gamer=request.user.gamerprofile,
            socialaccount=sociallogin.account,
        )


@receiver(updated_discord_social_account, sender=SocialAccount)
def create_or_update_server_list(
    sender, gamer, socialaccount, test_response=None, *args, **kwargs
):
    logger.debug("Sending async task to update gamer servers.")
    async_task(
        sync_discord_servers_from_discord_account,
        gamer,
        socialaccount,
        test_response=test_response,
    )


@receiver(post_delete, sender=SocialAccount)
def remove_discord_links(sender, instance, *args, **kwargs):
    logger.debug("signal evaluation social account provider")
    if instance.provider == "discord_with_guilds":  # pragma: no cover
        logger.debug("Sending async task to prune servers.")
        async_task(prune_servers)


@receiver(post_save, sender=SocialToken)
def add_discord_link_for_token(sender, instance, created, *args, **kwargs):
    if "discord" in instance.account.provider:
        if instance.token and instance.token_secret and instance.expires_at > timezone.now():
            try:
                gdl, created = GamerDiscordLink.objects.get_or_create(gamer=instance.account.user.gamerprofile, socialaccount=instance.account)
                if created:
                    logger.debug("Created one new GamerDiscordLink")
                    async_task(sync_discord_servers_from_discord_account, gdl.gamer, gdl.socialaccount)
            except IntegrityError:
                logger.debug("We tried to create a gamer discord link but another process beat us to the punch. the other process should take care of the rest.")
