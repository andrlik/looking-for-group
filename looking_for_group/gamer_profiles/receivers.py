import logging

import bleach
from bleach_whitelist.bleach_whitelist import markdown_attrs, markdown_tags
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from markdown import markdown
from notifications.signals import notify

from . import models
from ..discord.models import CommunityDiscordLink
from ..invites.signals import invite_accepted
from ..users.models import User

logger = logging.getLogger("gamer_profiles")


@receiver(pre_save, sender=models.GamerProfile)
def check_and_copy_username(sender, instance, *args, **kwargs):
    '''
    When saving, double check if we already have the cached username
    and add it if it is missing.
    '''
    if not instance.username and instance.user:
        instance.username = instance.user.username


@receiver(post_save, sender=User)
def copy_changed_username_to_gamerprofile(sender, instance, created, *args, **kwargs):
    if not created and instance.gamerprofile:
        instance.gamerprofile.username = instance.username
        instance.gamerprofile.save()


@receiver(pre_save, sender=models.GamerCommunity)
def generate_rendered_html_from_description(sender, instance, *args, **kwargs):
    """
    Parse the description with markdown and save the result.
    """
    if instance.description:
        logger.debug(
            "Found description for {}, rendering with markdown".format(instance.name)
        )
        instance.description_rendered = bleach.clean(
            markdown(instance.description, output_format="html5"),
            markdown_tags,
            markdown_attrs,
        )
    if instance.id and not instance.description:
        logger.debug(
            "Description is either not present or removed. Nulling out rendered html for {}".format(
                instance.name
            )
        )
        instance.description_rendered = None


@receiver(pre_save, sender=models.GamerNote)
def generate_rendered_note_body(sender, instance, *args, **kwargs):
    """
    Parse and convert markdown to rendered body.
    """
    if instance.body:
        logger.debug("Rendering markdown for note titled {}".format(instance.title))
        instance.body_rendered = bleach.clean(
            markdown(instance.body, output_format="html5"),
            markdown_tags,
            markdown_attrs,
        )


@receiver(post_save, sender=User)
def generate_default_gamer_profile(sender, instance, created, *args, **kwargs):
    """
    If a new user is created, generate an automatic gamer profile.
    """
    if created:
        logger.debug(
            "New user: Auto creating a related gamerprofile for user {}".format(
                instance.username
            )
        )
        models.GamerProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=models.GamerCommunity)
def add_owner_to_community(sender, instance, created, *args, **kwargs):
    """
    When creating or updating a community, make sure the owner is in the community.
    Owner MUST be an admin.
    """
    try:
        logger.debug("Community {0} save, checking owner".format(instance.name))
        role = instance.get_role(instance.owner)
        if role != "Admin":
            logger.debug(
                "Owner belongs to community {} but is not an admin. Rectifiying.".format(
                    instance.name
                )
            )
            instance.set_role(instance.owner, "admin")
    except models.NotInCommunity:
        logger.debug(
            "Ower is not in community {}; adding as admin".format(instance.name)
        )
        instance.add_member(instance.owner, role="admin")


@receiver(post_save, sender=models.GamerCommunity)
def create_placeholder_discord_link(sender, instance, created, *args, **kwargs):
    """
    add a placeholder object in the discord app. we use get_or_create to prevent duplicates.
    """
    if created:
        CommunityDiscordLink.objects.get_or_create(community=instance)


@receiver(post_save, sender=models.BlockedUser)
def remove_blocked_user_from_friends(sender, instance, created, *args, **kwargs):
    """
    When creating a new block record, remove from the blocker's friends list if present.
    """
    if created:
        instance.blocker.friends.remove(instance.blockee)


@receiver(invite_accepted)
def process_accepted_invite(sender, invite, acceptor, *args, **kwargs):
    if invite.content_type.name == "gamercommunity":
        logger.debug("Accepted invite was for a game community. Processing...")
        try:
            invite.content_object.add_member(acceptor.gamerprofile)
            notify.send(acceptor, recipient=invite.creator, verb="accepted your invite", target=invite.content_object)
            logger.debug("Gamer {} was added to community {}".format(acceptor.gamerprofile, invite.content_object.name))
        except models.AlreadyInCommunity:
            logger.debug("Gamer {} was already a member of {}. Moving on...".format(acceptor.gamerprofile, invite.content_object.name))
