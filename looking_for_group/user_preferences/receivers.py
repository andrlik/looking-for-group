from django.contrib.auth.models import Group
from django.db import models as django_models
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django_q.tasks import async_task
from haystack import signals
from notifications.signals import notify

from ..discord import models as discord_models
from ..gamer_profiles import models as social_models
from ..games import models as game_models
from ..users.models import User
from .models import Preferences


@receiver(post_save, sender=social_models.GamerProfile)
def create_initial_settings(sender, instance, created, *args, **kwargs):
    if created:
        pref = Preferences.objects.create(gamer=instance)
        notify.send(instance.user, recipient=instance.user, verb=_("has joined the party! Take a moment to review your settings here"), action_object=pref)


@receiver(post_save, sender=game_models.Player)
def check_for_new_player(sender, instance, created, *args, **kwargs):
    if created:
        notify.send(instance.game.gm, recipient=instance.gamer.user, verb=_("added you to game"), action_object=instance.game)


@receiver(post_save, sender=social_models.GamerFriendRequest)
def notify_if_new_request(sender, instance, created, *args, **kwargs):
    if created:
        notify.send(instance.requestor, recipient=instance.recipient.user, verb=_("sent you a friend request"))


@receiver(post_save, sender=social_models.KickedUser)
def notify_admins_on_kick(sender, instance, created, *args, **kwargs):
    if created:
        admins = instance.community.get_admins()
        for admin in admins:
            if admin.gamer != instance.kicker:
                notify.send(instance.kicker, recipient=admin.gamer.user, verb=_('kicked'), action_object=instance.kicked_user, target=instance.community)


@receiver(post_save, sender=social_models.BannedUser)
def notify_admins_on_ban(sender, instance, created, *args, **kwargs):
    if created:
        admins = instance.community.get_admins()
        for admin in admins:
            if admin.gamer != instance.banner:
                notify.send(instance.banner, recipient=admin.gamer.user, verb=_('banned'), action_object=instance.banned_user, target=instance.community)


@receiver(m2m_changed, sender=User.groups.through)
def notify_on_group_change(sender, instance, action, reverse, model, pk_set, *args, **kwargs):
    if action == 'post_add':
        if isinstance(instance, User):
            for pk in pk_set:
                notify.send(instance, recipient=instance, verb=_("you have been added to the permission group"), action_object=Group.objects.get(pk=pk))
    if action == "post_remove":
        if isinstance(instance, User):
            for pk in pk_set:
                notify.send(instance, recipient=instance, verb=_("you have been removed from the permission group"), action_object=Group.objects.get(pk=pk))


@receiver(post_save, sender=game_models.AdventureLog)
def notify_on_log_save(sender, instance, created, *args, **kwargs):
    editor = instance.initial_author
    verb = 'posted a new adventure log entry'
    if not created:
        editor = instance.last_edited_by
        verb = 'updated adventure log entry'
    game = instance.session.game
    for player in game.players.all():
        if player != editor:
            notify.send(editor, recipient=player.user, verb=verb, action_object=instance, target=game)


@receiver(m2m_changed, sender=discord_models.CommunityDiscordLink.servers.through)
def notify_admins_on_discord_server_change(sender, instance, action, reverse, model, pk_set, *args, **kwargs):
    if action in ["post_add", "post_remove"]:
        if action == 'post_add':
            verb = "linked discord server(s)"
        else:
            verb = "unlinked discord server(s)"
        if not reverse:
            admins = instance.community.get_admins()
            servers = social_models.GamerCommunity.objects.filter(id__in=pk_set)
            for admin in admins:
                for server in servers:
                    notify.send(instance.community, recipient=admin.gamer.user, verb=verb, action_object=server, target=instance.community)


class QueuedSignalProcessor(signals.BaseSignalProcessor):
    """
    Reindexing handles in a queue.
    """
    def setup(self):
        django_models.signals.post_save.connect(self.enqueue_save)
        django_models.signals.post_delete.connect(self.enqueue_delete)

    def teardown(self):
        django_models.signals.post_save.disconnect(self.enqueue_save)
        django_models.signals.post_delete.disconnect(self.enqueue_delete)

    def enqueue_save(self, sender, instance, **kwargs):
        async_task(self.handle_save)

    def enqueue_delete(self, sender, instance, **kwargs):
        async_task(self.handle_delete)
