from django.dispatch import receiver
from django_q.tasks import async_task
from django.db.models.signals import post_delete
from allauth.socialaccount.signals import social_account_added, social_account_updated
from allauth.socialaccount.models import SocialAccount
from .tasks import prune_servers, sync_discord_servers_from_discord_account


@receiver(social_account_added, sender=SocialAccount)
@receiver(social_account_updated, sender=SocialAccount)
def create_or_update_server_list(sender, request, socialaccount, *args, **kwargs):
    if socialaccount.provider == "discord_with_guilds":
        async_task(sync_discord_servers_from_discord_account, request, socialaccount)


@receiver(post_delete, sender=SocialAccount)
def remove_discord_links(sender, instance, *args, **kwargs):
    if instance.provider == "discord_with_guilds":
        async_task(prune_servers)
